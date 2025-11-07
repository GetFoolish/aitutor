import { useState, useEffect, useRef } from 'react';
import { Box, Icon, IconButton, useDisclosure, chakra } from '@chakra-ui/react';
import { motion, AnimatePresence, PanInfo } from 'framer-motion';
import { FaTimes, FaExpand, FaCompress } from 'react-icons/fa';
import {
  usePipecatClient,
  usePipecatClientTransportState,
} from "@pipecat-ai/client-react";

const MotionBox = chakra(motion.div);

interface AvatarVideoFeedProps {
  videoSocket?: WebSocket | null;
}

export function AvatarVideoFeed({ videoSocket }: AvatarVideoFeedProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [position, setPosition] = useState({ x: 20, y: 20 });
  const [size, setSize] = useState({ width: 180, height: 135 });
  const [isExpanded, setIsExpanded] = useState(false);
  const [isVisible, setIsVisible] = useState(true);

  // Pipecat hooks for connection status
  const client = usePipecatClient();
  const transportState = usePipecatClientTransportState();
  const isConnected = transportState === "ready" || transportState === "connected";

  // Handle dragging
  const handleDrag = (event: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
    setPosition({
      x: position.x + info.delta.x,
      y: position.y + info.delta.y,
    });
  };

  // Toggle expanded view
  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
    if (!isExpanded) {
      setSize({ width: 480, height: 360 });
    } else {
      setSize({ width: 180, height: 135 });
    }
  };

  // Listen for video frames from MediaMixer
  useEffect(() => {
    if (!videoSocket || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    console.log('[AvatarVideoFeed] Setting up video socket listener');

    const handleMessage = (event: MessageEvent) => {
      if (event.data instanceof Blob) {
        // Received video frame as blob
        const url = URL.createObjectURL(event.data);
        const img = new Image();

        img.onload = () => {
          // Draw frame to canvas
          canvas.width = size.width;
          canvas.height = size.height;
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          URL.revokeObjectURL(url);
        };

        img.src = url;
      }
    };

    videoSocket.addEventListener('message', handleMessage);

    return () => {
      videoSocket.removeEventListener('message', handleMessage);
    };
  }, [videoSocket, size]);

  if (!isVisible) return null;

  return (
    <AnimatePresence>
      <MotionBox
        position="fixed"
        top={`${position.y}px`}
        left={`${position.x}px`}
        zIndex={9998}
        drag
        dragMomentum={false}
        onDrag={handleDrag}
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0, opacity: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Box
          width={`${size.width}px`}
          height={`${size.height}px`}
          borderRadius="lg"
          overflow="hidden"
          boxShadow="0 8px 32px rgba(0, 0, 0, 0.6)"
          borderWidth="3px"
          borderColor={isConnected ? 'yellow.400' : 'gray.600'}
          bg="black"
          position="relative"
          cursor="move"
        >
          {/* Video Canvas */}
          <canvas
            ref={canvasRef}
            width={size.width}
            height={size.height}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />

          {/* Connection Status Indicator */}
          {!isConnected && (
            <Box
              position="absolute"
              top="50%"
              left="50%"
              transform="translate(-50%, -50%)"
              textAlign="center"
              color="white"
              fontSize="sm"
              fontWeight="bold"
              bg="blackAlpha.800"
              px={4}
              py={2}
              borderRadius="md"
            >
              Not Connected
            </Box>
          )}

          {/* Pulsing Border Animation when speaking */}
          {isConnected && transportState === "ready" && (
            <MotionBox
              position="absolute"
              top="0"
              left="0"
              right="0"
              bottom="0"
              borderRadius="lg"
              borderWidth="3px"
              borderColor="yellow.400"
              pointerEvents="none"
              animate={{
                opacity: [0.5, 1, 0.5],
                scale: [1, 1.02, 1],
              }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            />
          )}

          {/* Control Buttons */}
          <Box
            position="absolute"
            top="2"
            right="2"
            display="flex"
            gap={1}
            opacity={0.7}
            _hover={{ opacity: 1 }}
            transition="opacity 0.2s"
          >
            <IconButton
              aria-label="Toggle size"
              icon={<Icon as={isExpanded ? FaCompress : FaExpand} />}
              size="xs"
              colorScheme="blackAlpha"
              bg="blackAlpha.700"
              color="white"
              _hover={{ bg: 'blackAlpha.800' }}
              onClick={(e) => {
                e.stopPropagation();
                toggleExpanded();
              }}
            />
            <IconButton
              aria-label="Close"
              icon={<Icon as={FaTimes} />}
              size="xs"
              colorScheme="blackAlpha"
              bg="blackAlpha.700"
              color="white"
              _hover={{ bg: 'blackAlpha.800' }}
              onClick={(e) => {
                e.stopPropagation();
                setIsVisible(false);
              }}
            />
          </Box>

          {/* Label */}
          <Box
            position="absolute"
            bottom="2"
            left="2"
            bg="blackAlpha.700"
            color="white"
            fontSize="xs"
            px={2}
            py={1}
            borderRadius="md"
            fontWeight="bold"
          >
            AI Tutor
          </Box>
        </Box>
      </MotionBox>
    </AnimatePresence>
  );
}
