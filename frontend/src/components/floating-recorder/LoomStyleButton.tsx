import { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  Text,
  IconButton,
  useDisclosure,
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverBody,
  Button,
  HStack,
  useToast,
  Icon,
  chakra,
} from '@chakra-ui/react';
import { motion, AnimatePresence } from 'framer-motion';
import { FaVideo, FaDesktop, FaPencilAlt, FaTimes } from 'react-icons/fa';
import { ScratchpadModal } from './ScratchpadModal';
import {
  usePipecatClient,
  usePipecatClientTransportState,
} from "@pipecat-ai/client-react";

const MotionBox = chakra(motion.div);

interface LoomStyleButtonProps {
  commandSocket?: WebSocket | null;
}

export function LoomStyleButton({ commandSocket }: LoomStyleButtonProps) {
  const { isOpen: isScratchpadOpen, onOpen: onScratchpadOpen, onClose: onScratchpadClose } = useDisclosure();
  const toast = useToast();
  const [recordingState, setRecordingState] = useState({
    video: false,
    screenshare: false,
  });

  // Pipecat hooks
  const client = usePipecatClient();
  const transportState = usePipecatClientTransportState();

  const connected = transportState === "ready" || transportState === "connected";
  const isBotSpeaking = transportState === "ready"; // Bot is active and ready

  const handleVideoToggle = async () => {
    if (!recordingState.video) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        setRecordingState((prev) => ({ ...prev, video: true }));

        if (commandSocket && commandSocket.readyState === WebSocket.OPEN) {
          commandSocket.send(JSON.stringify({
            type: 'toggle_camera',
            data: { enabled: true }
          }));
        }

        toast({
          title: 'Camera enabled',
          status: 'success',
          duration: 2000,
        });
        (window as any).videoStream = stream;
      } catch (error) {
        toast({
          title: 'Camera access denied',
          status: 'error',
          duration: 3000,
        });
      }
    } else {
      const stream = (window as any).videoStream;
      if (stream) {
        stream.getTracks().forEach((track: MediaStreamTrack) => track.stop());
      }

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
      });
    }
  };

  const handleScreenshareToggle = async () => {
    if (!recordingState.screenshare) {
      try {
        const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
        setRecordingState((prev) => ({ ...prev, screenshare: true }));

        if (commandSocket && commandSocket.readyState === WebSocket.OPEN) {
          commandSocket.send(JSON.stringify({
            type: 'toggle_screen',
            data: { enabled: true }
          }));
        }

        toast({
          title: 'Screen sharing enabled',
          status: 'success',
          duration: 2000,
        });
        (window as any).screenshareStream = stream;
      } catch (error) {
        toast({
          title: 'Screen sharing cancelled',
          status: 'info',
          duration: 3000,
        });
      }
    } else {
      const stream = (window as any).screenshareStream;
      if (stream) {
        stream.getTracks().forEach((track: MediaStreamTrack) => track.stop());
      }

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
      });
    }
  };

  return (
    <>
      <Popover placement="top-end">
        <PopoverTrigger>
          <Box
            position="fixed"
            bottom="30px"
            right="30px"
            zIndex={9999}
          >
            {/* Loom-style Button */}
            <MotionBox
              w="60px"
              h="60px"
              borderRadius="full"
              bg="black"
              display="flex"
              alignItems="center"
              justifyContent="center"
              cursor="pointer"
              boxShadow="0 8px 32px rgba(0, 0, 0, 0.4)"
              position="relative"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
            >
              {/* Pulsing animation when bot is speaking */}
              <AnimatePresence>
                {isBotSpeaking && (
                  <>
                    <MotionBox
                      position="absolute"
                      w="100%"
                      h="100%"
                      borderRadius="full"
                      bg="yellow.400"
                      initial={{ scale: 1, opacity: 0.5 }}
                      animate={{
                        scale: [1, 1.5, 1],
                        opacity: [0.5, 0, 0.5],
                      }}
                      transition={{
                        duration: 1.5,
                        repeat: Infinity,
                        ease: "easeInOut",
                      }}
                    />
                    <MotionBox
                      position="absolute"
                      w="100%"
                      h="100%"
                      borderRadius="full"
                      bg="yellow.400"
                      initial={{ scale: 1, opacity: 0.3 }}
                      animate={{
                        scale: [1, 1.8, 1],
                        opacity: [0.3, 0, 0.3],
                      }}
                      transition={{
                        duration: 1.5,
                        repeat: Infinity,
                        ease: "easeInOut",
                        delay: 0.5,
                      }}
                    />
                  </>
                )}
              </AnimatePresence>

              {/* Center dot - changes color based on connection */}
              <MotionBox
                w="24px"
                h="24px"
                borderRadius="full"
                bg={connected ? "yellow.400" : "gray.600"}
                animate={
                  connected
                    ? {
                        scale: [1, 1.2, 1],
                      }
                    : {}
                }
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeInOut",
                }}
              />

              {/* Status indicator */}
              {(recordingState.video || recordingState.screenshare) && (
                <Box
                  position="absolute"
                  top="-2px"
                  right="-2px"
                  w="16px"
                  h="16px"
                  borderRadius="full"
                  bg="red.500"
                  border="2px solid white"
                />
              )}
            </MotionBox>
          </Box>
        </PopoverTrigger>

        <PopoverContent
          bg="black"
          borderColor="gray.700"
          borderWidth="1px"
          color="white"
          w="280px"
          mr={4}
          mb={2}
        >
          <PopoverBody p={4}>
            <VStack spacing={3} align="stretch">
              <Text fontSize="sm" fontWeight="bold" mb={2}>
                AI Tutor Tools
              </Text>

              <Button
                leftIcon={<FaVideo />}
                size="sm"
                variant={recordingState.video ? "solid" : "outline"}
                colorScheme={recordingState.video ? "green" : "gray"}
                onClick={handleVideoToggle}
                justifyContent="flex-start"
                bg={recordingState.video ? "green.500" : "transparent"}
                borderColor="gray.600"
                _hover={{ bg: recordingState.video ? "green.600" : "gray.800" }}
              >
                {recordingState.video ? 'Stop Camera' : 'Start Camera'}
              </Button>

              <Button
                leftIcon={<FaDesktop />}
                size="sm"
                variant={recordingState.screenshare ? "solid" : "outline"}
                colorScheme={recordingState.screenshare ? "green" : "gray"}
                onClick={handleScreenshareToggle}
                justifyContent="flex-start"
                bg={recordingState.screenshare ? "green.500" : "transparent"}
                borderColor="gray.600"
                _hover={{ bg: recordingState.screenshare ? "green.600" : "gray.800" }}
              >
                {recordingState.screenshare ? 'Stop Sharing' : 'Share Screen'}
              </Button>

              <Button
                leftIcon={<FaPencilAlt />}
                size="sm"
                variant="outline"
                colorScheme="purple"
                onClick={onScratchpadOpen}
                justifyContent="flex-start"
                borderColor="gray.600"
                _hover={{ bg: "purple.900" }}
              >
                Open Scratchpad
              </Button>

              <Box pt={2} borderTop="1px" borderColor="gray.700">
                <HStack fontSize="xs" color="gray.400" justify="center">
                  <Box w="8px" h="8px" borderRadius="full" bg={connected ? "green.400" : "gray.600"} />
                  <Text>{connected ? 'AI Connected' : 'Disconnected'}</Text>
                </HStack>
              </Box>
            </VStack>
          </PopoverBody>
        </PopoverContent>
      </Popover>

      <ScratchpadModal
        isOpen={isScratchpadOpen}
        onClose={onScratchpadClose}
        commandSocket={commandSocket}
      />
    </>
  );
}
