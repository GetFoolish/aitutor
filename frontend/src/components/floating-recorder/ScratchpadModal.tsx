import { useRef, useEffect, useState } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  Button,
  HStack,
  IconButton,
  Tooltip,
  VStack,
  Text,
  useColorMode,
} from '@chakra-ui/react';
import { FaTrash } from 'react-icons/fa';

interface ScratchpadModalProps {
  isOpen: boolean;
  onClose: () => void;
  commandSocket?: WebSocket | null;
}

export function ScratchpadModal({ isOpen, onClose, commandSocket }: ScratchpadModalProps) {
  const { colorMode } = useColorMode();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [currentColor, setCurrentColor] = useState('#000000');
  const [lineWidth, setLineWidth] = useState(3);

  // Initialize canvas once when opened
  useEffect(() => {
    if (!canvasRef.current || !isOpen) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    canvas.width = 800;
    canvas.height = 600;

    // Set white background
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Set drawing properties
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
  }, [isOpen]);

  // Send scratchpad frames to MediaMixer periodically
  useEffect(() => {
    if (!isOpen || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const intervalId = setInterval(() => {
      if (commandSocket && commandSocket.readyState === WebSocket.OPEN) {
        const imageData = canvas.toDataURL('image/jpeg', 0.8);
        commandSocket.send(JSON.stringify({
          type: 'scratchpad_frame',
          data: imageData
        }));
      }
    }, 200); // Send at ~5 FPS

    return () => clearInterval(intervalId);
  }, [isOpen, commandSocket]);

  const startDrawing = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.beginPath();
    ctx.moveTo(x, y);
    setIsDrawing(true);
  };

  const draw = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.strokeStyle = currentColor;
    ctx.lineWidth = lineWidth;
    ctx.lineTo(x, y);
    ctx.stroke();
  };

  const stopDrawing = () => {
    setIsDrawing(false);
  };

  const clearCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  };

  const colors = [
    '#000000', // Black
    '#FF0000', // Red
    '#0000FF', // Blue
    '#00FF00', // Green
    '#FFFF00', // Yellow
    '#FF00FF', // Magenta
    '#00FFFF', // Cyan
    '#FFA500', // Orange
  ];

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="4xl">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Scratchpad - Draw Your Work</ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          <VStack spacing={4} align="stretch">
            <Text fontSize="sm" color="gray.500">
              Use this space to work out problems, draw diagrams, or take notes while learning
            </Text>

            <HStack spacing={4} wrap="wrap">
              <HStack>
                <Text fontSize="sm" fontWeight="bold">Color:</Text>
                {colors.map((color) => (
                  <Tooltip key={color} label={color} placement="top">
                    <Button
                      size="sm"
                      w="30px"
                      h="30px"
                      p={0}
                      bg={color}
                      border={currentColor === color ? '3px solid' : '1px solid'}
                      borderColor={currentColor === color ? 'blue.500' : 'gray.300'}
                      onClick={() => setCurrentColor(color)}
                      _hover={{ transform: 'scale(1.1)' }}
                    />
                  </Tooltip>
                ))}
              </HStack>

              <HStack>
                <Text fontSize="sm" fontWeight="bold">Size:</Text>
                {[2, 3, 5, 8].map((width) => (
                  <Button
                    key={width}
                    size="sm"
                    variant={lineWidth === width ? 'solid' : 'outline'}
                    colorScheme={lineWidth === width ? 'blue' : 'gray'}
                    onClick={() => setLineWidth(width)}
                  >
                    {width}px
                  </Button>
                ))}
              </HStack>

              <Tooltip label="Clear canvas" placement="top">
                <IconButton
                  aria-label="Clear canvas"
                  icon={<FaTrash />}
                  size="sm"
                  colorScheme="red"
                  variant="outline"
                  onClick={clearCanvas}
                />
              </Tooltip>
            </HStack>

            <canvas
              ref={canvasRef}
              onMouseDown={startDrawing}
              onMouseMove={draw}
              onMouseUp={stopDrawing}
              onMouseLeave={stopDrawing}
              style={{
                border: `2px solid ${colorMode === 'dark' ? '#4A5568' : '#E2E8F0'}`,
                borderRadius: '8px',
                cursor: 'crosshair',
                backgroundColor: '#ffffff',
                width: '100%',
                height: 'auto',
                maxHeight: '500px',
              }}
            />
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}
