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
const CONVERSATIONS_PATH = join(rootDir, 'data', 'conversations');

if (!existsSync(CONVERSATIONS_PATH)) {
  mkdirSync(CONVERSATIONS_PATH, { recursive: true });
}

let SYSTEM_PROMPT = '';
try {
  SYSTEM_PROMPT = readFileSync(join(__dirname, 'system_prompts/adam_tutor.md'), 'utf-8');
  console.log(`📝 System prompt loaded (${SYSTEM_PROMPT.length} characters)`);
} catch (error) {
  console.error('⚠️  Warning: Could not load system prompt file:', error.message);
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
    this.filepath = join(CONVERSATIONS_PATH, `${sessionId}.json`);
    this.userBuffer = '';
    this.adamBuffer = '';
    
    this._save();
    console.log(`📝 Conversation session started: ${sessionId}`);
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

  flushUserTurn() {
    if (!this.session || !this.userBuffer.trim()) return;
    
    this.session.turns.push({
      speaker: 'user',
      text: this.userBuffer.trim(),
      timestamp: new Date().toISOString()
    });
    console.log(`🎤 User turn saved: ${this.userBuffer.trim().substring(0, 50)}...`);
    this.userBuffer = '';
    this._save();
  }

  flushAdamTurn() {
    if (!this.session || !this.adamBuffer.trim()) return;
    
    this.session.turns.push({
      speaker: 'adam',
      text: this.adamBuffer.trim(),
      timestamp: new Date().toISOString()
    });
    console.log(`🤖 Adam turn saved: ${this.adamBuffer.trim().substring(0, 50)}...`);
    this.adamBuffer = '';
    this._save();
  }

  _save() {
    if (!this.session || !this.filepath) return;
    try {
      writeFileSync(this.filepath, JSON.stringify(this.session, null, 2), 'utf-8');
    } catch (error) {
      console.error('❌ Failed to save conversation:', error.message);
    }
  }

  endSession() {
    if (!this.session) return null;
    
    // Flush any remaining buffers
    this.flushUserTurn();
    this.flushAdamTurn();
    
    this.session.end_time = new Date().toISOString();
    this._save();
    console.log(`💾 Conversation ended: ${this.filepath}`);
    
    const sessionId = this.session.session_id;
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
  console.log(`📁 Conversations path: ${CONVERSATIONS_PATH}`);
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
              onmessage: (geminiMessage) => {
                if (geminiMessage.serverContent) {
                  // Buffer user input transcription chunks
                  if (geminiMessage.serverContent.inputTranscription?.text) {
                    conversationManager.appendUserChunk(geminiMessage.serverContent.inputTranscription.text);
                  }
                  
                  // Buffer adam output transcription chunks
                  if (geminiMessage.serverContent.outputTranscription?.text) {
                    conversationManager.appendAdamChunk(geminiMessage.serverContent.outputTranscription.text);
                  }
                  
                  // On turn complete, flush the adam buffer
                  if (geminiMessage.serverContent.turnComplete) {
                    conversationManager.flushAdamTurn();
                  }
                  
                  // On interrupted (user started speaking), flush user buffer from previous and adam buffer
                  if (geminiMessage.serverContent.interrupted) {
                    conversationManager.flushAdamTurn();
                  }
                }
                
                clientWs.send(JSON.stringify({ type: 'message', data: geminiMessage }));
              },
              onerror: (error) => {
                console.error('❌ Gemini error:', error.message);
                clientWs.send(JSON.stringify({ type: 'error', error: error.message }));
              },
              onclose: (event) => {
                console.log(`🔌 Gemini connection closed: ${event.reason || 'Unknown reason'}`);
                conversationManager.endSession();
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
          conversationManager.endSession();
          geminiSession.close();
          geminiSession = null;
          console.log('🔌 Gemini session closed');
        }
      }
      
      else if (message.type === 'realtimeInput') {
        if (geminiSession) {
          // When user sends audio, flush any pending user transcription from previous turn
          if (message.data?.mimeType?.includes('audio')) {
            conversationManager.flushUserTurn();
          }
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

  clientWs.on('close', () => {
    console.log('🔌 Frontend client disconnected');
    conversationManager.endSession();
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
