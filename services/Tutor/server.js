import { GoogleGenAI } from '@google/genai';
import { WebSocketServer } from 'ws';
import http from 'http';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import dotenv from 'dotenv';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = join(__dirname, '../..');

try {
  dotenv.config({ path: join(rootDir, '.env') });
} catch (error) {}

const PORT = process.env.PORT || 8767;
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const GEMINI_MODEL = process.env.GEMINI_MODEL || 'models/gemini-2.5-flash-native-audio-preview-09-2025';
const CONVERSATIONS_BASE_PATH = join(rootDir, 'services', 'TeachingAssistant', 'Memory', 'data');
const TEACHING_ASSISTANT_API_URL = process.env.TEACHING_ASSISTANT_API_URL || 'http://localhost:8002';

if (!existsSync(CONVERSATIONS_BASE_PATH)) {
  mkdirSync(CONVERSATIONS_BASE_PATH, { recursive: true });
}

let SYSTEM_PROMPT = '';
try {
  SYSTEM_PROMPT = readFileSync(join(__dirname, 'system_prompts/adam_tutor.md'), 'utf-8');
  console.log(`📝 System prompt loaded (${SYSTEM_PROMPT.length} characters)`);
} catch (error) {
  console.error('⚠️  Warning: Could not load system prompt file:', error.message);
}

// Helper function to send memory events (non-blocking)
async function sendMemoryEvent(endpoint, data) {
  try {
    const response = await fetch(`${TEACHING_ASSISTANT_API_URL}/memory/${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) {
      console.error(`⚠️  Memory event failed: ${endpoint} - ${response.statusText}`);
    }
  } catch (error) {
    // Silently fail - don't block conversation flow
    console.error(`⚠️  Failed to send memory event to ${endpoint}:`, error.message);
  }
}

// Helper function to trigger memory retrieval (blocking)
async function triggerMemoryRetrieval(sessionId, userId, userText, timestamp, adamText = '') {
  try {
    const response = await fetch(`${TEACHING_ASSISTANT_API_URL}/memory/retrieval/user-turn`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        user_id: userId,
        user_text: userText,
        timestamp: timestamp,
        adam_text: adamText
      })
    });
    
    if (!response.ok) {
      console.error(`⚠️  Memory retrieval request failed: ${response.statusText}`);
    }
  } catch (error) {
    // Silently fail - don't block conversation flow
    console.error(`⚠️  Failed to trigger memory retrieval:`, error.message);
  }
}

// Helper function to get memory injection (blocking, returns injection text)
async function getMemoryInjection(sessionId, userId, userText = '', timestamp = '', adamText = '') {
  try {
    const response = await fetch(`${TEACHING_ASSISTANT_API_URL}/memory/retrieval/user-turn`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        user_id: userId,
        user_text: userText,  // Empty means just get stored injection
        timestamp: timestamp || new Date().toISOString(),
        adam_text: adamText
      })
    });
    
    if (!response.ok) {
      let errorText = '';
      try {
        errorText = await response.text();
      } catch (e) {
        errorText = 'Unable to read error response';
      }
      console.error(`⚠️  Memory injection request failed: ${response.status} ${response.statusText}`);
      if (errorText && errorText.length > 0) {
        console.error(`⚠️  Error details: ${errorText.substring(0, 300)}`);
      }
      return null;
    }
    
    const data = await response.json();
    return data.injection_text || null;
  } catch (error) {
    // Silently fail - don't block conversation flow
    console.error(`⚠️  Failed to get memory injection:`, error.message);
    if (error.stack) {
      console.error(`⚠️  Stack:`, error.stack);
    }
    return null;
  }
}

class ConversationManager {
  constructor() {
    this.session = null;
    this.filepath = null;
    this.userBuffer = '';
    this.adamBuffer = '';
  }

  startSession(userId = 'anonymous') {
    const timestamp = new Date();
    const randomSuffix = Math.random().toString(36).substring(2, 8);
    const sessionId = `sess_${timestamp.toISOString().slice(0, 19).replace(/[-:T]/g, '').replace(/(\d{8})(\d{6})/, '$1_$2')}_${randomSuffix}`;
    
    this.session = {
      session_id: sessionId,
      user_id: userId,
      start_time: timestamp.toISOString(),
      end_time: null,
      turns: []
    };
    
    // Create user_id-based path: data/{userId}/conversations/
    const userConversationsPath = join(CONVERSATIONS_BASE_PATH, userId, 'conversations');
    if (!existsSync(userConversationsPath)) {
      mkdirSync(userConversationsPath, { recursive: true });
    }
    this.filepath = join(userConversationsPath, `${sessionId}.json`);
    this.userBuffer = '';
    this.adamBuffer = '';
    
    this._save();
    console.log(`📝 Conversation session started: ${sessionId} for user: ${userId}`);
    
    // Send real-time event to memory system
    sendMemoryEvent('session/start', {
      session_id: sessionId,
      user_id: userId
    });
    
    return sessionId;
  }

  appendUserChunk(text) {
    if (!this.session || !text) return;
    this.userBuffer += text;
  }

  appendAdamChunk(text) {
    if (!this.session || !text) return;
    this.adamBuffer += text;
  }

  async flushUserTurn() {
    if (!this.session || !this.userBuffer.trim()) return null;
    
    const userText = this.userBuffer.trim();
    const timestamp = new Date().toISOString();
    
    this.session.turns.push({
      speaker: 'user',
      text: userText,
      timestamp: timestamp
    });
    console.log(`🎤 User turn saved: ${userText.substring(0, 50)}...`);
    this.userBuffer = '';
    this._save();
    
    // Trigger memory retrieval (stores results in memory for later injection)
    // Don't inject yet - wait until Adam stops speaking
    await triggerMemoryRetrieval(
      this.session.session_id,
      this.session.user_id,
      userText,
      timestamp,
      ''  // adam_text will be empty at this point
    );
    
    return { userText, timestamp };
  }

  async injectMemoriesForNextTurn(geminiSession) {
    if (!this.session || !geminiSession) {
      console.log(`⚠️  [INJECTION] Cannot inject: missing session or geminiSession`);
      return;
    }
    
    console.log(`💉 [INJECTION] Attempting to inject memories for session ${this.session.session_id}`);
    
    try {
      // Small delay to ensure retrieval from flushUserTurn() has completed
      await new Promise(resolve => setTimeout(resolve, 200)); // 200ms delay
      
      // Get memory injection from stored retrieval results (no new retrieval, just get stored)
      const injectionText = await getMemoryInjection(
        this.session.session_id,
        this.session.user_id,
        '',  // Empty user_text means just get stored injection
        new Date().toISOString(),
        this.adamBuffer.trim()  // Use Adam's last response if available
      );
      
      // If injection text exists, send it to Gemini (after Adam stops, before next user turn)
      if (injectionText) {
        console.log(`💉 [INJECTION] Injecting memory context after Adam stopped (${injectionText.length} chars)`);
        
        // Send injection as a user message - Gemini will process it as context
        // The triple curly braces format tells Gemini to use it silently
        try {
          geminiSession.sendClientContent({
            turns: [{
              role: 'user',
              parts: [{ text: injectionText }]
            }],
            turnComplete: true
          });
          console.log(`✅ [INJECTION] Memory injection sent successfully to Gemini`);
        } catch (sendError) {
          console.error(`⚠️  [INJECTION] Failed to send to Gemini:`, sendError.message);
          throw sendError;
        }
      } else {
        console.log(`ℹ️  [INJECTION] No injection text returned (all memories may already be injected or retrieval not complete)`);
      }
    } catch (error) {
      console.error(`⚠️  [INJECTION] Failed to inject memory:`, error.message);
      if (error.stack) {
        console.error(`⚠️  [INJECTION] Error stack:`, error.stack);
      }
    }
  }

  flushAdamTurn() {
    if (!this.session || !this.adamBuffer.trim()) return;
    
    const adamText = this.adamBuffer.trim();
    const timestamp = new Date().toISOString();
    
    this.session.turns.push({
      speaker: 'adam',
      text: adamText,
      timestamp: timestamp
    });
    console.log(`🤖 Adam turn saved: ${adamText.substring(0, 50)}...`);
    this.adamBuffer = '';
    this._save();
    
    // Get last user turn for memory extraction event
    const lastUserTurn = this.session.turns
      .slice()
      .reverse()
      .find(t => t.speaker === 'user');
    
    // Send real-time event for memory extraction (complete exchange)
    sendMemoryEvent('turn', {
      session_id: this.session.session_id,
      user_id: this.session.user_id,
      user_text: lastUserTurn?.text || '',
      adam_text: adamText,
      timestamp: timestamp
    });
  }

  _save() {
    if (!this.session || !this.filepath) return;
    try {
      writeFileSync(this.filepath, JSON.stringify(this.session, null, 2), 'utf-8');
    } catch (error) {
      console.error('❌ Failed to save conversation:', error.message);
    }
  }

  async endSession() {
    if (!this.session) return null;
    
    // Flush any remaining buffers
    await this.flushUserTurn();
    this.flushAdamTurn();
    
    const endTime = new Date().toISOString();
    this.session.end_time = endTime;
    this._save();
    console.log(`💾 Conversation ended: ${this.filepath}`);
    
    const sessionId = this.session.session_id;
    const userId = this.session.user_id;
    
    // Send real-time event
    sendMemoryEvent('session/end', {
      session_id: sessionId,
      user_id: userId,
      end_time: endTime
    });
    
    this.session = null;
    this.filepath = null;
    return sessionId;
  }
}

const server = http.createServer((req, res) => {
  if (req.method === 'GET' && (req.url === '/' || req.url === '/health')) {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('OK');
    return;
  }
  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Not Found');
});

const wss = new WebSocketServer({ noServer: true });

server.on('upgrade', (request, socket, head) => {
  wss.handleUpgrade(request, socket, head, (ws) => {
    wss.emit('connection', ws, request);
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`🎓 Adam Tutor Service started on port ${PORT}`);
  console.log(`🤖 Using model: ${GEMINI_MODEL}`);
  console.log(`📁 Conversations base path: ${CONVERSATIONS_BASE_PATH}`);
  if (!GEMINI_API_KEY) {
    console.warn('⚠️  WARNING: GEMINI_API_KEY not set.');
  }
});

server.on('error', (error) => {
  console.error('❌ Server error:', error);
  process.exit(1);
});

wss.on('connection', (clientWs) => {
  console.log('✅ Frontend client connected');
  
  let geminiSession = null;
  let geminiClient = null;
  const conversationManager = new ConversationManager();

  clientWs.on('message', async (data) => {
    try {
      const message = JSON.parse(data.toString());
      
      if (message.type === 'connect') {
        if (!GEMINI_API_KEY) {
          clientWs.send(JSON.stringify({ type: 'error', error: 'GEMINI_API_KEY not configured' }));
          return;
        }
        
        const { config } = message;
        geminiClient = new GoogleGenAI({ apiKey: GEMINI_API_KEY });
        
        const fullConfig = {
          ...config,
          systemInstruction: config.systemInstruction || SYSTEM_PROMPT,
          inputAudioTranscription: {},
          outputAudioTranscription: {}
        };
        
        console.log(`🔗 Connecting to Gemini model: ${GEMINI_MODEL}`);
        
        try {
          conversationManager.startSession(message.userId || 'anonymous');
          
          geminiSession = await geminiClient.live.connect({
            model: GEMINI_MODEL,
            config: fullConfig,
            callbacks: {
              onopen: () => {
                console.log('✅ Gemini Live API connected');
                clientWs.send(JSON.stringify({ type: 'open' }));
              },
              onmessage: async (geminiMessage) => {
                if (geminiMessage.serverContent) {
                  // Buffer user input transcription chunks
                  if (geminiMessage.serverContent.inputTranscription?.text) {
                    conversationManager.appendUserChunk(geminiMessage.serverContent.inputTranscription.text);
                  }
                  
                  // When Adam starts speaking, flush the user buffer first
                  if (geminiMessage.serverContent.outputTranscription?.text) {
                    // Flush user turn before Adam's response (user finished speaking)
                    await conversationManager.flushUserTurn();
                    conversationManager.appendAdamChunk(geminiMessage.serverContent.outputTranscription.text);
                  }
                  
                  // On turn complete (Adam stops speaking), inject memories for next user turn
                  if (geminiMessage.serverContent.turnComplete) {
                    console.log(`🛑 [INJECTION] Adam turn complete - triggering memory injection`);
                    conversationManager.flushAdamTurn();
                    // Inject memories after Adam stops speaking (user's turn is coming)
                    await conversationManager.injectMemoriesForNextTurn(geminiSession);
                  }
                  
                  // On interrupted (user started speaking), flush adam buffer and inject memories
                  if (geminiMessage.serverContent.interrupted) {
                    console.log(`🛑 [INJECTION] Adam interrupted - triggering memory injection`);
                    conversationManager.flushAdamTurn();
                    // Inject memories after Adam stops speaking (user's turn is coming)
                    await conversationManager.injectMemoriesForNextTurn(geminiSession);
                  }
                }
                
                clientWs.send(JSON.stringify({ type: 'message', data: geminiMessage }));
              },
              onerror: (error) => {
                console.error('❌ Gemini error:', error.message);
                clientWs.send(JSON.stringify({ type: 'error', error: error.message }));
              },
              onclose: async (event) => {
                console.log(`🔌 Gemini connection closed: ${event.reason || 'Unknown reason'}`);
                await conversationManager.endSession();
                clientWs.send(JSON.stringify({ type: 'close', reason: event.reason }));
              }
            }
          });
          
          console.log('✅ Gemini session established with transcription enabled');
        } catch (error) {
          console.error('❌ Failed to connect to Gemini:', error.message);
          clientWs.send(JSON.stringify({ type: 'error', error: `Failed to connect: ${error.message}` }));
        }
      }
      
      else if (message.type === 'disconnect') {
        if (geminiSession) {
          await conversationManager.endSession();
          geminiSession.close();
          geminiSession = null;
          console.log('🔌 Gemini session closed');
        }
      }
      
      else if (message.type === 'realtimeInput') {
        if (geminiSession) {
          geminiSession.sendRealtimeInput({ media: message.data });
        }
      }
      
      else if (message.type === 'toolResponse') {
        if (geminiSession) {
          geminiSession.sendToolResponse(message.data);
        }
      }
      
      else if (message.type === 'send') {
        if (geminiSession) {
          geminiSession.sendClientContent({
            turns: message.parts,
            turnComplete: message.turnComplete !== false
          });
        }
      }
      
    } catch (error) {
      console.error('❌ Error processing message:', error);
      clientWs.send(JSON.stringify({ type: 'error', error: error.message }));
    }
  });

  clientWs.on('close', async () => {
    console.log('🔌 Frontend client disconnected');
    await conversationManager.endSession();
    if (geminiSession) {
      geminiSession.close();
      geminiSession = null;
    }
  });

  clientWs.on('error', (error) => {
    console.error('❌ WebSocket error:', error);
  });
});

const shutdown = () => {
  console.log('\n🛑 Shutting down Adam Tutor Service...');
  wss.close(() => {
    server.close(() => {
      console.log('✅ Server closed');
      process.exit(0);
    });
  });
};

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
