import { GoogleGenAI } from '@google/genai';
import { WebSocketServer } from 'ws';
import http from 'http';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import dotenv from 'dotenv';
import crypto from 'crypto';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = join(__dirname, '../..');

try {
  dotenv.config({ path: join(rootDir, '.env') });
} catch (error) {}

const PORT = process.env.PORT || 8767;
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const GEMINI_MODEL = process.env.GEMINI_MODEL || 'models/gemini-2.5-flash-native-audio-preview-09-2025';

let SYSTEM_PROMPT = '';
try {
  SYSTEM_PROMPT = readFileSync(join(__dirname, 'system_prompts/adam_tutor.md'), 'utf-8');
  console.log(`📝 System prompt loaded (${SYSTEM_PROMPT.length} characters)`);
} catch (error) {
  console.error('⚠️  Warning: Could not load system prompt file:', error.message);
}

const activeSessions = new Map();
const teachingAssistantClients = new Set();

// Message sequencing and tracking
let messageSequenceCounter = 0;
const messageStats = {
  totalSent: 0,
  totalFailed: 0,
  totalDropped: 0
};

function generateMessageId() {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 11);
  return `msg_${timestamp}_${++messageSequenceCounter}_${random}`;
}

// Session locks for synchronization
const sessionLocks = new Map();

function getSessionLock(sessionId) {
  if (!sessionLocks.has(sessionId)) {
    sessionLocks.set(sessionId, { locked: false, processing: false });
  }
  return sessionLocks.get(sessionId);
}

async function acquireSessionLock(sessionId) {
  const lock = getSessionLock(sessionId);
  const maxWait = 1000; // 1 second max wait
  const startTime = Date.now();
  
  while (lock.locked && (Date.now() - startTime) < maxWait) {
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  
  if (lock.locked) {
    console.warn(`⚠️ Timeout waiting for session lock: ${sessionId}`);
    return false;
  }
  
  lock.locked = true;
  lock.processing = true;
  return true;
}

function releaseSessionLock(sessionId) {
  const lock = sessionLocks.get(sessionId);
  if (lock) {
    lock.locked = false;
    lock.processing = false;
  }
}

function generateSessionId() {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 11);
  return `sess_${timestamp}_${random}`;
}

function createSession(sessionId, userId, geminiSession, clientWs) {
  activeSessions.set(sessionId, {
    sessionId,
    userId,
    geminiSession,
    clientWs,
    startTime: new Date(),
    lastActivity: new Date(),
    lastSpeaker: null,
    transcriptions: {
      user: {
        current: '',
        complete: [],
        lastComplete: null,
        firstChunkTime: null
      },
      adam: {
        current: '',
        complete: [],
        lastComplete: null,
        firstChunkTime: null
      }
    }
  });
}

function getSession(sessionId) {
  return activeSessions.get(sessionId) || null;
}

function removeSession(sessionId) {
  activeSessions.delete(sessionId);
}

function getSessionByClientWs(clientWs) {
  for (const [sessionId, session] of activeSessions.entries()) {
    if (session.clientWs === clientWs) {
      return session;
    }
  }
  return null;
}

function extractTranscriptions(geminiMessage) {
  if (!geminiMessage || !geminiMessage.serverContent) {
    return null;
  }

  const content = geminiMessage.serverContent;
  const result = {
    user: null,
    adam: null,
    turnComplete: false,
    interrupted: false
  };

  if (content.inputTranscription && content.inputTranscription.text !== undefined) {
    result.user = {
      text: content.inputTranscription.text || '',
      timestamp: new Date()
    };
  }

  if (content.outputTranscription && content.outputTranscription.text !== undefined) {
    result.adam = {
      text: content.outputTranscription.text || '',
      timestamp: new Date()
    };
  }

  if (content.turnComplete === true) {
    result.turnComplete = true;
  }

  if (content.interrupted === true) {
    result.interrupted = true;
  }

  return (result.user || result.adam || result.turnComplete || result.interrupted) ? result : null;
}

async function storeTranscriptions(session, transcriptions) {
  if (!session || !session.transcriptions || !transcriptions) {
    return;
  }

  const lockAcquired = await acquireSessionLock(session.sessionId);
  if (!lockAcquired) {
    console.error(`❌ Failed to acquire lock for session ${session.sessionId}, skipping transcription`);
    return;
  }

  try {
    const now = new Date();
    const timestamp = now.toISOString();
    const timeMs = now.getTime();
    
    if (transcriptions.user && transcriptions.user.text) {
      if (!session.transcriptions.user.firstChunkTime) {
        session.transcriptions.user.firstChunkTime = timeMs;
      }
      session.transcriptions.user.current += transcriptions.user.text;
      console.log(`📝 [${timestamp}] User transcription chunk: "${transcriptions.user.text.substring(0, 50)}${transcriptions.user.text.length > 50 ? '...' : ''}" (accumulated: ${session.transcriptions.user.current.length} chars, first chunk at: ${session.transcriptions.user.firstChunkTime})`);
    }

    if (transcriptions.adam && transcriptions.adam.text) {
      if (!session.transcriptions.adam.firstChunkTime) {
        session.transcriptions.adam.firstChunkTime = timeMs;
      }
      session.transcriptions.adam.current += transcriptions.adam.text;
      console.log(`📝 [${timestamp}] Adam transcription chunk: "${transcriptions.adam.text.substring(0, 50)}${transcriptions.adam.text.length > 50 ? '...' : ''}" (accumulated: ${session.transcriptions.adam.current.length} chars, first chunk at: ${session.transcriptions.adam.firstChunkTime})`);
    }

    if (transcriptions.turnComplete || transcriptions.interrupted) {
      const turnCompleteTime = timeMs;
      console.log(`✅ [${timestamp}] Turn complete detected (turnComplete timestamp: ${turnCompleteTime}) - broadcasting accumulated turns IMMEDIATELY`);
      
      if (session.transcriptions.user.current.trim()) {
        const completeUserText = session.transcriptions.user.current.trim();
        const firstChunkTime = session.transcriptions.user.firstChunkTime || turnCompleteTime;
        const timeDiff = turnCompleteTime - firstChunkTime;
        
        console.log(`📤 [${timestamp}] Broadcasting USER turn (${completeUserText.length} chars, first chunk: ${firstChunkTime}, turnComplete: ${turnCompleteTime}, delay: ${timeDiff}ms): "${completeUserText.substring(0, 100)}${completeUserText.length > 100 ? '...' : ''}"`);
        
        broadcastToTeachingAssistant({
          type: 'text',
          data: {
            session_id: session.sessionId,
            user_id: session.userId,
            text: completeUserText,
            speaker: 'user',
            timestamp: timestamp
          }
        });
        
        session.transcriptions.user.complete.push({
          text: completeUserText,
          timestamp: now
        });
        session.transcriptions.user.lastComplete = session.transcriptions.user.complete[session.transcriptions.user.complete.length - 1];
        session.transcriptions.user.current = '';
        session.transcriptions.user.firstChunkTime = null;
        session.lastSpeaker = 'user';
      }

      if (session.transcriptions.adam.current.trim()) {
        const completeAdamText = session.transcriptions.adam.current.trim();
        const firstChunkTime = session.transcriptions.adam.firstChunkTime || turnCompleteTime;
        const timeDiff = turnCompleteTime - firstChunkTime;
        
        console.log(`📤 [${timestamp}] Broadcasting ADAM turn (${completeAdamText.length} chars, first chunk: ${firstChunkTime}, turnComplete: ${turnCompleteTime}, delay: ${timeDiff}ms): "${completeAdamText.substring(0, 100)}${completeAdamText.length > 100 ? '...' : ''}"`);
        
        broadcastToTeachingAssistant({
          type: 'text',
          data: {
            session_id: session.sessionId,
            user_id: session.userId,
            text: completeAdamText,
            speaker: 'adam',
            interrupted: transcriptions.interrupted || false,
            timestamp: timestamp
          }
        });
        
        session.transcriptions.adam.complete.push({
          text: completeAdamText,
          timestamp: now
        });
        session.transcriptions.adam.lastComplete = session.transcriptions.adam.complete[session.transcriptions.adam.complete.length - 1];
        session.transcriptions.adam.current = '';
        session.transcriptions.adam.firstChunkTime = null;
        session.lastSpeaker = 'adam';
      }
    }
  } finally {
    releaseSessionLock(session.sessionId);
  }
}

function broadcastToTeachingAssistant(event) {
  if (teachingAssistantClients.size === 0) {
    console.warn('⚠️ No TeachingAssistant clients connected, message not sent');
    messageStats.totalDropped++;
    return;
  }

  const messageId = generateMessageId();
  const sequence = messageSequenceCounter;
  const enrichedEvent = {
    ...event,
    message_id: messageId,
    sequence: sequence,
    server_timestamp: new Date().toISOString()
  };

  let message;
  try {
    const messageWithoutChecksum = JSON.stringify(enrichedEvent);
    const checksum = crypto.createHash('sha256').update(messageWithoutChecksum).digest('hex');
    enrichedEvent.checksum = checksum;
    message = JSON.stringify(enrichedEvent);
  } catch (error) {
    console.error(`❌ Failed to serialize message ${messageId}:`, error);
    messageStats.totalFailed++;
    return;
  }

  const deadClients = [];
  let successCount = 0;
  let failureCount = 0;

  for (const client of teachingAssistantClients) {
    if (client.readyState === 1) {
      try {
        client.send(message);
        successCount++;
      } catch (error) {
        console.error(`❌ Failed to send message ${messageId} (seq: ${sequence}) to client:`, error.message);
        deadClients.push(client);
        failureCount++;
      }
    } else {
      deadClients.push(client);
      failureCount++;
    }
  }

  deadClients.forEach(client => teachingAssistantClients.delete(client));
  
  messageStats.totalSent += successCount;
  messageStats.totalFailed += failureCount;
  
  if (successCount > 0) {
    console.log(`📤 Broadcast message ${messageId} (seq: ${sequence}, type: ${event.type}) - Success: ${successCount}, Failed: ${failureCount}`);
  }
  
  if (failureCount > 0) {
    console.warn(`⚠️ Message ${messageId} failed to reach ${failureCount} client(s)`);
  }
  
  if (event.type === 'text' && event.data?.text) {
    const textPreview = event.data.text.substring(0, 50);
    console.log(`   └─ Text preview: "${textPreview}${event.data.text.length > 50 ? '...' : ''}"`);
  }
}

function parseJSONBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => {
      body += chunk.toString();
    });
    req.on('end', () => {
      try {
        resolve(JSON.parse(body));
      } catch (error) {
        reject(new Error('Invalid JSON'));
      }
    });
    req.on('error', reject);
  });
}

const server = http.createServer(async (req, res) => {
  const urlPath = req.url?.split('?')[0] || '/';

  if (req.method === 'GET' && (urlPath === '/' || urlPath === '/health')) {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('OK');
    return;
  }

  if (req.method === 'OPTIONS') {
    res.writeHead(200, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    });
    res.end();
    return;
  }

  if (req.method === 'POST' && urlPath === '/send_message_to_adam') {
    try {
      const body = await parseJSONBody(req);
      const { session_id, user_id, message } = body;

      if (!session_id) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'session_id is required' }));
        return;
      }

      if (!message) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'message is required' }));
        return;
      }

      const session = getSession(session_id);
      if (!session) {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Session not found' }));
        return;
      }

      if (user_id && session.userId !== user_id) {
        res.writeHead(403, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'User ID mismatch' }));
        return;
      }

      try {
        session.geminiSession.sendClientContent({
          turns: [{
            role: 'user',
            parts: [{ text: message }]
          }],
          turnComplete: true
        });

        session.lastActivity = new Date();

        console.log(`✅ Injected to session ${session_id}`);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          status: 'sent',
          session_id: session_id
        }));
      } catch (geminiError) {
        console.error(`❌ Injection failed: ${session_id}`);
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          error: 'Failed to send message to Gemini',
          details: geminiError.message
        }));
      }
    } catch (error) {
      console.error(`❌ Injection error: ${error.message}`);
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Internal server error' }));
    }
    return;
  }

  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Not Found');
});

const wss = new WebSocketServer({ noServer: true });
const taWss = new WebSocketServer({ noServer: true });

server.on('upgrade', (request, socket, head) => {
  const urlPath = new URL(request.url, `http://${request.headers.host}`).pathname;

  if (urlPath === '/ta') {
    taWss.handleUpgrade(request, socket, head, (ws) => {
      taWss.emit('connection', ws, request);
    });
  } else {
    wss.handleUpgrade(request, socket, head, (ws) => {
      wss.emit('connection', ws, request);
    });
  }
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`🎓 Adam Tutor Service started on port ${PORT}`);
  console.log(`🤖 Using model: ${GEMINI_MODEL}`);
  if (!GEMINI_API_KEY) {
    console.warn('⚠️  WARNING: GEMINI_API_KEY not set.');
  }
});

server.on('error', (error) => {
  if (error.code === 'EADDRINUSE') {
    console.error(`❌ Port ${PORT} is already in use`);
  } else {
    console.error('❌ Server error:', error);
  }
  process.exit(1);
});

wss.on('connection', (clientWs) => {
  console.log('✅ Frontend client connected');
  
  let geminiSession = null;
  let geminiClient = null;

  clientWs.on('message', async (data) => {
    try {
      const message = JSON.parse(data.toString());
      
      if (message.type === 'connect') {
        if (!GEMINI_API_KEY) {
          clientWs.send(JSON.stringify({ type: 'error', error: 'GEMINI_API_KEY not configured' }));
          return;
        }
        
        const { config, user_id } = message;
        const sessionId = generateSessionId();
        const userId = user_id || 'anonymous';
        
        clientWs.sessionId = sessionId;
        clientWs.userId = userId;
        
        geminiClient = new GoogleGenAI({ apiKey: GEMINI_API_KEY });
        
        const fullConfig = {
          ...config,
          systemInstruction: config.systemInstruction || SYSTEM_PROMPT,
          inputAudioTranscription: {},
          outputAudioTranscription: {}
        };
        
        console.log(`🔗 Connecting to Gemini model: ${GEMINI_MODEL}`);
        
        try {
          geminiSession = await geminiClient.live.connect({
            model: GEMINI_MODEL,
            config: fullConfig,
            callbacks: {
              onopen: () => {
                console.log('✅ Gemini Live API connected');
                clientWs.send(JSON.stringify({ type: 'open' }));
              },
              onmessage: async (geminiMessage) => {
                clientWs.send(JSON.stringify({ type: 'message', data: geminiMessage }));

                const transcriptions = extractTranscriptions(geminiMessage);
                if (transcriptions) {
                  const session = getSessionByClientWs(clientWs);
                  if (session) {
                    storeTranscriptions(session, transcriptions);
                  }
                }
              },
              onerror: (error) => {
                console.error('❌ Gemini error:', error.message);
                clientWs.send(JSON.stringify({ type: 'error', error: error.message }));
              },
              onclose: async (event) => {
                console.log(`🔌 Gemini connection closed: ${event.reason || 'Unknown reason'}`);
                clientWs.send(JSON.stringify({ type: 'close', reason: event.reason }));
              }
            }
          });
          
          createSession(sessionId, userId, geminiSession, clientWs);
          clientWs.send(JSON.stringify({
            type: 'session_created',
            session_id: sessionId,
            user_id: userId
          }));

          broadcastToTeachingAssistant({
            type: 'session_start',
            data: {
              session_id: sessionId,
              user_id: userId,
              timestamp: new Date().toISOString()
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
    
    const sessionId = clientWs.sessionId;
    const userId = clientWs.userId;
    
    if (sessionId) {
      broadcastToTeachingAssistant({
        type: 'session_end',
        data: {
          session_id: sessionId,
          user_id: userId || 'anonymous',
          timestamp: new Date().toISOString()
        }
      });
      
      removeSession(sessionId);
    }
    
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
  taWss.close(() => {
    wss.close(() => {
      server.close(() => {
        console.log('✅ Server closed');
        process.exit(0);
      });
    });
  });
};

taWss.on('connection', (taWs) => {
  teachingAssistantClients.add(taWs);

  taWs.on('close', () => {
    teachingAssistantClients.delete(taWs);
  });

  taWs.on('error', (error) => {
    console.error('❌ TeachingAssistant WebSocket error:', error);
    teachingAssistantClients.delete(taWs);
  });
});

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
