import { GoogleGenAI } from '@google/genai';
import { WebSocketServer } from 'ws';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import dotenv from 'dotenv';

// Load environment variables from root .env
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = join(__dirname, '../..');
dotenv.config({ path: join(rootDir, '.env') });

const PORT = 8767;
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const GEMINI_MODEL = process.env.GEMINI_MODEL || 'models/gemini-2.5-flash-native-audio-preview-09-2025';

if (!GEMINI_API_KEY) {
  console.error('❌ ERROR: GEMINI_API_KEY not found in root .env file');
  process.exit(1);
}

// Load system prompt
const SYSTEM_PROMPT = readFileSync(
  join(__dirname, 'system_prompts/adam_tutor.md'),
  'utf-8'
);

// WebSocket server for frontend connections
const wss = new WebSocketServer({ port: PORT });

console.log(`🎓 Adam Tutor Service started on ws://localhost:${PORT}`);
console.log(`📝 System prompt loaded (${SYSTEM_PROMPT.length} characters)`);
console.log(`🤖 Using model: ${GEMINI_MODEL}`);

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

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 Shutting down Adam Tutor Service...');
  wss.close(() => {
    console.log('✅ Server closed');
    process.exit(0);
  });
});

