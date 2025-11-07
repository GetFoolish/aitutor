import { useState, useRef } from 'react';
import {
  Box,
  IconButton,
  VStack,
  Tooltip,
  useColorMode,
  useToast,
  Text,
  Badge,
  useDisclosure,
  HStack,
  chakra,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import {
  FaVideo,
  FaDesktop,
  FaPencilAlt,
  FaMicrophone,
  FaMicrophoneSlash,
} from 'react-icons/fa';
import Draggable from 'react-draggable';
import { ScratchpadModal } from './ScratchpadModal';
import {
  usePipecatClient,
  usePipecatClientTransportState,
} from "@pipecat-ai/client-react";

const MotionBox = chakra(motion.div);

interface RecordingState {
  video: boolean;
  screenshare: boolean;
  scratchpad: boolean;
}

interface FloatingRecorderProps {
  commandSocket?: WebSocket | null;
}

export function FloatingRecorder({ commandSocket }: FloatingRecorderProps) {
  const { colorMode } = useColorMode();
  const toast = useToast();
  const { isOpen: isScratchpadOpen, onOpen: onScratchpadOpen, onClose: onScratchpadClose } = useDisclosure();
  const [isExpanded, setIsExpanded] = useState(false);
  const [recordingState, setRecordingState] = useState<RecordingState>({
    video: false,
    screenshare: false,
    scratchpad: false,
  });
  const [position, setPosition] = useState({ x: 20, y: 20 });
  const nodeRef = useRef(null);

  // Pipecat hooks
  const client = usePipecatClient();
  const transportState = usePipecatClientTransportState();

  const connected = transportState === "ready" || transportState === "connected";
  const isConnecting = transportState === "initializing" || transportState === "authenticating";

  const handleVideoToggle = async () => {
    if (!recordingState.video) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        setRecordingState((prev) => ({ ...prev, video: true }));

        // Notify MediaMixer to start camera
        if (commandSocket && commandSocket.readyState === WebSocket.OPEN) {
          commandSocket.send(JSON.stringify({
            type: 'toggle_camera',
            data: { enabled: true }
          }));
        }

        toast({
          title: 'Camera enabled',
          description: 'Your webcam is now active',
          status: 'success',
          duration: 2000,
          isClosable: true,
        });
        (window as any).videoStream = stream;
      } catch (error) {
        toast({
          title: 'Camera access denied',
          description: 'Please enable camera permissions in your browser',
          status: 'error',
          duration: 3000,
          isClosable: true,
        });
      }
    } else {
      const stream = (window as any).videoStream;
      if (stream) {
        stream.getTracks().forEach((track: MediaStreamTrack) => track.stop());
      }

      // Notify MediaMixer to stop camera
      if (commandSocket && commandSocket.readyState === WebSocket.OPEN) {
        commandSocket.send(JSON.stringify({
          type: 'toggle_camera',
          data: { enabled: false }
        }));
      }

      setRecordingState((prev) => ({ ...prev, video: false }));
      toast({
        title: 'Camera disabled',
        status: 'info',
        duration: 2000,
        isClosable: true,
      });
    }
  };

  const handleScreenshareToggle = async () => {
    if (!recordingState.screenshare) {
      try {
        const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
        setRecordingState((prev) => ({ ...prev, screenshare: true }));

        // Notify MediaMixer to start screen share
        if (commandSocket && commandSocket.readyState === WebSocket.OPEN) {
          commandSocket.send(JSON.stringify({
            type: 'toggle_screen',
            data: { enabled: true }
          }));
        }

        toast({
          title: 'Screen sharing enabled',
          description: 'The AI can now see your screen',
          status: 'success',
          duration: 2000,
          isClosable: true,
        });
        (window as any).screenshareStream = stream;
      } catch (error) {
        toast({
          title: 'Screen sharing cancelled',
          status: 'info',
          duration: 3000,
          isClosable: true,
        });
      }
    } else {
      const stream = (window as any).screenshareStream;
      if (stream) {
        stream.getTracks().forEach((track: MediaStreamTrack) => track.stop());
      }

      // Notify MediaMixer to stop screen share
      if (commandSocket && commandSocket.readyState === WebSocket.OPEN) {
        commandSocket.send(JSON.stringify({
          type: 'toggle_screen',
          data: { enabled: false }
        }));
      }

      setRecordingState((prev) => ({ ...prev, screenshare: false }));
      toast({
        title: 'Screen sharing disabled',
        status: 'info',
        duration: 2000,
        isClosable: true,
      });
    }
  };

  const handleScratchpadToggle = () => {
    onScratchpadOpen();
    setRecordingState((prev) => ({ ...prev, scratchpad: true }));
  };

  return (
    <>
      <Draggable
        nodeRef={nodeRef}
        position={position}
        onStop={(_, data) => {
          setPosition({ x: data.x, y: data.y });
        }}
        bounds="parent"
      >
        <Box
          ref={nodeRef}
          position="fixed"
          bottom="20px"
          right="20px"
          zIndex={9999}
          cursor="grab"
          _active={{ cursor: 'grabbing' }}
        >
          <MotionBox
            onMouseEnter={() => setIsExpanded(true)}
            onMouseLeave={() => setIsExpanded(false)}
            animate={{
              width: isExpanded ? '280px' : '70px',
              height: isExpanded ? 'auto' : '70px',
            }}
            transition={{ duration: 0.2 }}
            bg={colorMode === 'dark' ? 'gray.700' : 'white'}
            borderRadius={isExpanded ? 'lg' : 'full'}
            boxShadow="2xl"
            border="2px solid"
            borderColor={connected ? 'green.500' : isConnecting ? 'yellow.500' : 'blue.500'}
            overflow="hidden"
          >
            {isExpanded ? (
              <VStack spacing={3} p={4} align="stretch">
                <Box>
                  <Text fontSize="sm" fontWeight="bold" mb={1}>
                    AI Tutor Tools
                  </Text>
                  <Text fontSize="xs" color="gray.500" mb={2}>
                    Hover to expand • Drag to move
                  </Text>
                  {connected && (
                    <HStack spacing={1} mb={2}>
                      <Badge colorScheme="green" fontSize="xs">Connected</Badge>
                    </HStack>
                  )}
                  {isConnecting && (
                    <HStack spacing={1} mb={2}>
                      <Badge colorScheme="yellow" fontSize="xs">Connecting...</Badge>
                    </HStack>
                  )}
                </Box>

                <Tooltip label="Voice AI Tutor - Use Connect button in panel" placement="left" hasArrow>
                  <Box>
                    <IconButton
                      aria-label="Voice Tutor Status"
                      icon={connected ? <FaMicrophone /> : <FaMicrophoneSlash />}
                      colorScheme={connected ? 'green' : 'gray'}
                      size="lg"
                      width="100%"
                      isDisabled
                    />
                    <Text fontSize="xs" textAlign="center" mt={1} color="gray.500">
                      {connected ? '✓ AI Ready' : 'Voice Tutor'}
                    </Text>
                  </Box>
                </Tooltip>

                <Tooltip label="Enable your webcam" placement="left" hasArrow>
                  <Box>
                    <IconButton
                      aria-label="Toggle Camera"
                      icon={<FaVideo />}
                      size="md"
                      width="100%"
                      colorScheme={recordingState.video ? 'green' : 'gray'}
                      onClick={handleVideoToggle}
                    />
                    <Text fontSize="xs" textAlign="center" mt={1} color="gray.500">
                      {recordingState.video ? '✓ Camera' : 'Camera'}
                    </Text>
                  </Box>
                </Tooltip>

                <Tooltip label="Share your screen" placement="left" hasArrow>
                  <Box>
                    <IconButton
                      aria-label="Toggle Screen Share"
                      icon={<FaDesktop />}
                      size="md"
                      width="100%"
                      colorScheme={recordingState.screenshare ? 'green' : 'gray'}
                      onClick={handleScreenshareToggle}
                    />
                    <Text fontSize="xs" textAlign="center" mt={1} color="gray.500">
                      {recordingState.screenshare ? '✓ Sharing' : 'Screen'}
                    </Text>
                  </Box>
                </Tooltip>

                <Tooltip label="Open drawing scratchpad" placement="left" hasArrow>
                  <Box>
                    <IconButton
                      aria-label="Open Scratchpad"
                      icon={<FaPencilAlt />}
                      size="md"
                      width="100%"
                      colorScheme="purple"
                      onClick={handleScratchpadToggle}
                    />
                    <Text fontSize="xs" textAlign="center" mt={1} color="gray.500">
                      Scratchpad
                    </Text>
                  </Box>
                </Tooltip>
              </VStack>
            ) : (
              <Box p={2} display="flex" alignItems="center" justifyContent="center">
                <Tooltip label="AI Tutor Tools - Hover to Expand" placement="left" hasArrow>
                  <IconButton
                    aria-label="AI Tutor Tools"
                    icon={connected ? <FaMicrophone /> : <FaMicrophoneSlash />}
                    colorScheme={connected ? 'green' : 'blue'}
                    borderRadius="full"
                    size="lg"
                    onClick={() => setIsExpanded(true)}
                  />
                </Tooltip>
              </Box>
            )}
          </MotionBox>
        </Box>
      </Draggable>

      <ScratchpadModal
        isOpen={isScratchpadOpen}
        onClose={() => {
          onScratchpadClose();
          setRecordingState((prev) => ({ ...prev, scratchpad: false }));
        }}
        commandSocket={commandSocket}
      />
    </>
  );
}
