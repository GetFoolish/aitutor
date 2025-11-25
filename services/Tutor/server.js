import { GoogleGenAI } from '@google/genai';
import { WebSocketServer } from 'ws';
import http from 'http';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import dotenv from 'dotenv';

// Load environment variables from root .env (optional - Cloud Run uses env vars directly)
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = join(__dirname, '../..');
try {
  dotenv.config({ path: join(rootDir, '.env') });
} catch (error) {
  // .env file is optional - Cloud Run provides env vars directly
  // This is fine for local development too if .env doesn't exist
}

const PORT = process.env.PORT || 8767;
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const GEMINI_MODEL = process.env.GEMINI_MODEL || 'models/gemini-2.5-flash-native-audio-preview-09-2025';

// Load system prompt (with error handling)
let SYSTEM_PROMPT = '';
try {
  SYSTEM_PROMPT = readFileSync(
    join(__dirname, 'system_prompts/adam_tutor.md'),
    'utf-8'
  );
  console.log(`📝 System prompt loaded (${SYSTEM_PROMPT.length} characters)`);
} catch (error) {
  console.error('⚠️  Warning: Could not load system prompt file:', error.message);
  console.log('📝 Using empty system prompt (will use default from config)');
}

// Create HTTP server for health checks (required by Cloud Run)
const server = http.createServer((req, res) => {
  // Health check endpoint
  if (req.method === 'GET' && (req.url === '/' || req.url === '/health')) {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('OK');
    return;
  }
  // For any other requests, return 404
  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Not Found');
});

// Create WebSocket server attached to HTTP server
const wss = new WebSocketServer({ noServer: true });

// Handle WebSocket upgrade requests
// Cloud Run supports WebSocket upgrades on any path
server.on('upgrade', (request, socket, head) => {
  // Accept WebSocket upgrade on any path (root path is used by frontend)
  wss.handleUpgrade(request, socket, head, (ws) => {
    wss.emit('connection', ws, request);
  });
});

// Start the HTTP server (which also handles WebSocket upgrades)
// IMPORTANT: Server must start listening immediately for Cloud Run health checks
server.listen(PORT, '0.0.0.0', () => {
  console.log(`🎓 Adam Tutor Service started on port ${PORT}`);
  console.log(`🌐 HTTP server listening on http://0.0.0.0:${PORT}`);
  console.log(`💚 Health check available at http://0.0.0.0:${PORT}/health`);
  console.log(`🔌 WebSocket server ready on ws://0.0.0.0:${PORT}`);
  console.log(`🤖 Using model: ${GEMINI_MODEL}`);
  if (!GEMINI_API_KEY) {
    console.warn('⚠️  WARNING: GEMINI_API_KEY not set. WebSocket connections will fail.');
  }
});

// Handle server errors
server.on('error', (error) => {
  console.error('❌ Server error:', error);
  process.exit(1);
});

wss.on('connection', (clientWs) => {
  console.log('✅ Frontend client connected');
  
  let geminiSession = null;
  let geminiClient = null;

  // Handle messages from frontend
  clientWs.on('message', async (data) => {
    try {
      const message = JSON.parse(data.toString());
      
      // Handle connection request
      if (message.type === 'connect') {
        if (!GEMINI_API_KEY) {
          clientWs.send(JSON.stringify({
            type: 'error',
            error: 'GEMINI_API_KEY not configured'
          }));
          return;
        }
        
        const { config } = message;
        
        // Initialize Gemini client
        geminiClient = new GoogleGenAI({ apiKey: GEMINI_API_KEY });
        
        // Inject system prompt into config
        const fullConfig = {
          ...config,
          systemInstruction: config.systemInstruction || SYSTEM_PROMPT,
        };
        
        console.log(`🔗 Connecting to Gemini model: ${GEMINI_MODEL}`);
        console.log(`🎤 Voice: ${fullConfig.speechConfig?.voiceConfig?.prebuiltVoiceConfig?.voiceName || 'default'}`);
        
        // Connect to Gemini Live API
        try {
          geminiSession = await geminiClient.live.connect({
            model: GEMINI_MODEL,
            config: fullConfig,
            callbacks: {
              onopen: () => {
                console.log('✅ Gemini Live API connected');
                clientWs.send(JSON.stringify({ type: 'open' }));
              },
              onmessage: (geminiMessage) => {
                // Forward Gemini messages to frontend
                clientWs.send(JSON.stringify({
                  type: 'message',
                  data: geminiMessage
                }));
              },
              onerror: (error) => {
                console.error('❌ Gemini error:', error.message);
                clientWs.send(JSON.stringify({
                  type: 'error',
                  error: error.message
                }));
              },
              onclose: (event) => {
                console.log(`🔌 Gemini connection closed: ${event.reason || 'Unknown reason'}`);
                clientWs.send(JSON.stringify({
                  type: 'close',
                  reason: event.reason
                }));
              }
            }
          });
          
          console.log('✅ Gemini session established');
        } catch (error) {
          console.error('❌ Failed to connect to Gemini:', error.message);
          clientWs.send(JSON.stringify({
            type: 'error',
            error: `Failed to connect: ${error.message}`
          }));
        }
      }
      
      // Handle disconnect request
      else if (message.type === 'disconnect') {
        if (geminiSession) {
          geminiSession.close();
          geminiSession = null;
          console.log('🔌 Gemini session closed');
        }
      }
      
      // Handle realtime input (audio/video)
      else if (message.type === 'realtimeInput') {
        if (geminiSession) {
          geminiSession.sendRealtimeInput({ media: message.data });
        }
      }
      
      // Handle tool response
      else if (message.type === 'toolResponse') {
        if (geminiSession) {
          geminiSession.sendToolResponse(message.data);
        }
      }
      
      // Handle client content (text messages)
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
      clientWs.send(JSON.stringify({
        type: 'error',
        error: error.message
      }));
    }
  });

  clientWs.on('close', () => {
    console.log('🔌 Frontend client disconnected');
    if (geminiSession) {
      geminiSession.close();
      geminiSession = null;
    }
  });

  clientWs.on('error', (error) => {
    console.error('❌ WebSocket error:', error);
  });
});

// Graceful shutdown handler
const shutdown = () => {
  console.log('\n🛑 Shutting down Adam Tutor Service...');
  wss.close(() => {
    server.close(() => {
      console.log('✅ Server closed');
      process.exit(0);
    });
  });
};

// Handle both SIGINT (local dev) and SIGTERM (Cloud Run)
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

