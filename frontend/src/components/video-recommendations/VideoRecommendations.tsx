import { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Image,
  Badge,
  Spinner,
  Icon,
  Button,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  useDisclosure,
  AspectRatio,
} from '@chakra-ui/react';
import { FaYoutube, FaPlay, FaCheckCircle } from 'react-icons/fa';

interface Video {
  video_id: string;
  title: string;
  url: string;
  thumbnail_url: string;
  duration: number;
  view_count: number;
  channel_title: string;
  description: string;
  match_score: number;
  transcript_available: boolean;
  language: string;
  region: string;
}

interface VideoRecommendationsProps {
  skillIds?: string[];
  skillName?: string;
  maxVideos?: number;
}

export function VideoRecommendations({
  skillIds = [],
  skillName,
  maxVideos = 3,
}: VideoRecommendationsProps) {
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedVideo, setSelectedVideo] = useState<Video | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();

  useEffect(() => {
    if (skillIds.length > 0 || skillName) {
      fetchVideoRecommendations();
    }
  }, [skillIds, skillName]);

  const fetchVideoRecommendations = async () => {
    setLoading(true);
    try {
      let response;

      if (skillName) {
        // Use skill name directly
        response = await fetch('http://localhost:8002/recommend', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            skill_name: skillName,
            max_videos: maxVideos,
            min_match_score: 60,
          }),
        });
      } else if (skillIds.length > 0) {
        // Use first skill ID
        response = await fetch(
          `http://localhost:8002/recommendations/${skillIds[0]}?max_videos=${maxVideos}&min_match_score=60`
        );
      } else {
        return;
      }

      if (response.ok) {
        const data = await response.json();
        setVideos(data);
      }
    } catch (error) {
      console.error('Failed to fetch video recommendations:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const formatViewCount = (count: number): string => {
    if (count >= 1000000) {
      return `${(count / 1000000).toFixed(1)}M views`;
    } else if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}K views`;
    }
    return `${count} views`;
  };

  const openVideo = (video: Video) => {
    setSelectedVideo(video);
    onOpen();
  };

  if (loading) {
    return (
      <Box p={4} textAlign="center">
        <Spinner size="lg" color="yellow.400" />
        <Text mt={2} color="gray.400" fontSize="sm">
          Finding helpful videos...
        </Text>
      </Box>
    );
  }

  if (videos.length === 0) {
    return (
      <Box p={4} textAlign="center">
        <Icon as={FaYoutube} boxSize={12} color="gray.600" mb={2} />
        <Text color="gray.500" fontSize="sm">
          No video recommendations available
        </Text>
      </Box>
    );
  }

  return (
    <>
      <VStack spacing={3} align="stretch">
        {videos.map((video) => (
          <Box
            key={video.video_id}
            borderRadius="lg"
            borderWidth="2px"
            borderColor="gray.700"
            bg="gray.900"
            overflow="hidden"
            cursor="pointer"
            onClick={() => openVideo(video)}
            _hover={{
              borderColor: 'yellow.400',
              transform: 'translateY(-2px)',
            }}
            transition="all 0.2s"
          >
            <HStack spacing={0} align="stretch">
              {/* Thumbnail */}
              <Box position="relative" w="180px" flexShrink={0}>
                <Image
                  src={video.thumbnail_url}
                  alt={video.title}
                  objectFit="cover"
                  w="full"
                  h="100px"
                />
                <Box
                  position="absolute"
                  bottom="2"
                  right="2"
                  bg="black"
                  color="white"
                  fontSize="xs"
                  px={1}
                  borderRadius="sm"
                  fontWeight="bold"
                >
                  {formatDuration(video.duration)}
                </Box>
                <Box
                  position="absolute"
                  top="50%"
                  left="50%"
                  transform="translate(-50%, -50%)"
                >
                  <Icon as={FaPlay} boxSize={8} color="white" opacity={0.8} />
                </Box>
              </Box>

              {/* Video Info */}
              <VStack align="start" spacing={1} p={3} flex={1}>
                <Text
                  fontSize="sm"
                  fontWeight="bold"
                  color="white"
                  noOfLines={2}
                  lineHeight="1.3"
                >
                  {video.title}
                </Text>

                <HStack spacing={2} flexWrap="wrap">
                  <Badge colorScheme="yellow" fontSize="xs">
                    {Math.round(video.match_score)}% Match
                  </Badge>
                  {video.transcript_available && (
                    <Badge colorScheme="green" fontSize="xs">
                      <Icon as={FaCheckCircle} mr={1} boxSize={2} />
                      Transcript
                    </Badge>
                  )}
                </HStack>

                <Text fontSize="xs" color="gray.400" noOfLines={1}>
                  {video.channel_title}
                </Text>

                <Text fontSize="xs" color="gray.500">
                  {formatViewCount(video.view_count)}
                </Text>
              </VStack>
            </HStack>
          </Box>
        ))}
      </VStack>

      {/* Video Player Modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="6xl">
        <ModalOverlay />
        <ModalContent bg="black" color="white">
          <ModalHeader>{selectedVideo?.title}</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            {selectedVideo && (
              <VStack spacing={4} align="stretch">
                <AspectRatio ratio={16 / 9}>
                  <iframe
                    src={`https://www.youtube.com/embed/${selectedVideo.video_id}?autoplay=1`}
                    title={selectedVideo.title}
                    allowFullScreen
                    style={{ borderRadius: '8px' }}
                  />
                </AspectRatio>

                <HStack justify="space-between">
                  <VStack align="start" spacing={1}>
                    <Text fontSize="sm" color="gray.400">
                      {selectedVideo.channel_title}
                    </Text>
                    <HStack spacing={3} fontSize="xs" color="gray.500">
                      <Text>{formatViewCount(selectedVideo.view_count)}</Text>
                      <Text>•</Text>
                      <Text>{formatDuration(selectedVideo.duration)}</Text>
                    </HStack>
                  </VStack>

                  <Button
                    as="a"
                    href={selectedVideo.url}
                    target="_blank"
                    colorScheme="red"
                    leftIcon={<FaYoutube />}
                    size="sm"
                  >
                    Watch on YouTube
                  </Button>
                </HStack>

                <Box>
                  <Text fontSize="sm" color="gray.300">
                    {selectedVideo.description}
                  </Text>
                </Box>
              </VStack>
            )}
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
}
