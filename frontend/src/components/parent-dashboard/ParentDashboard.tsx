import { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  HStack,
  Heading,
  Text,
  Button,
  Card,
  CardHeader,
  CardBody,
  Grid,
  GridItem,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Badge,
  Progress,
  useColorMode,
  useToast,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  FormControl,
  FormLabel,
  Input,
  useDisclosure,
  Flex,
  Icon,
  Divider,
} from '@chakra-ui/react';
import {
  FaChild,
  FaPlus,
  FaTrophy,
  FaChartLine,
  FaClock,
  FaCheckCircle,
} from 'react-icons/fa';
import { useAuth } from '../../contexts/AuthContext';

interface Child {
  user_id: string;
  name: string;
  age: number;
  credits: number;
  created_at: string;
}

interface ChildStats {
  total_questions: number;
  correct_answers: number;
  accuracy: number;
  skills_mastered: number;
  total_skills: number;
  avg_response_time: number;
  last_activity: string;
}

export function ParentDashboard() {
  const { user, token } = useAuth();
  const { colorMode } = useColorMode();
  const toast = useToast();
  const { isOpen, onOpen, onClose } = useDisclosure();

  const [children, setChildren] = useState<Child[]>([]);
  const [selectedChild, setSelectedChild] = useState<Child | null>(null);
  const [childStats, setChildStats] = useState<Record<string, ChildStats>>({});
  const [loading, setLoading] = useState(true);

  // New child form
  const [childName, setChildName] = useState('');
  const [childAge, setChildAge] = useState('');

  useEffect(() => {
    if (user && user.account_type === 'parent') {
      fetchChildren();
    }
  }, [user]);

  const fetchChildren = async () => {
    if (!user || !token) return;

    setLoading(true);
    try {
      // Fetch children IDs from user profile
      const childPromises = user.children.map((childId: string) =>
        fetch(`http://localhost:8001/auth/user/${childId}`, {
          headers: { Authorization: `Bearer ${token}` },
        }).then((res) => res.json())
      );

      const childrenData = await Promise.all(childPromises);
      setChildren(childrenData);

      // Fetch stats for each child
      const statsPromises = childrenData.map((child: Child) =>
        fetch(`http://localhost:8000/skill-states/${child.user_id}`)
          .then((res) => res.json())
          .then((data) => {
            const skills = data.skills || [];
            const mastered = skills.filter((s: any) => s.memory_strength >= 0.8).length;

            return {
              childId: child.user_id,
              stats: {
                total_questions: skills.reduce((sum: number, s: any) => sum + s.practice_count, 0),
                correct_answers: skills.reduce((sum: number, s: any) => sum + s.correct_count, 0),
                accuracy: 0.85, // TODO: Calculate from actual data
                skills_mastered: mastered,
                total_skills: skills.length,
                avg_response_time: 45, // TODO: Get from actual data
                last_activity: new Date().toISOString(),
              },
            };
          })
      );

      const statsResults = await Promise.all(statsPromises);
      const statsMap: Record<string, ChildStats> = {};
      statsResults.forEach((result) => {
        statsMap[result.childId] = result.stats;
      });
      setChildStats(statsMap);
    } catch (error: any) {
      toast({
        title: 'Error fetching children',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateChild = async () => {
    if (!childName || !childAge) {
      toast({
        title: 'Missing information',
        description: 'Please enter child name and age',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    try {
      const response = await fetch('http://localhost:8001/auth/parent/create-child', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: childName,
          age: parseInt(childAge),
          language: 'en',
          region: 'US',
        }),
      });

      if (response.ok) {
        toast({
          title: 'Child account created!',
          status: 'success',
          duration: 3000,
        });

        setChildName('');
        setChildAge('');
        onClose();
        fetchChildren();
      } else {
        const error = await response.json();
        throw new Error(error.detail);
      }
    } catch (error: any) {
      toast({
        title: 'Failed to create child account',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  if (!user || user.account_type !== 'parent') {
    return (
      <Box p={8}>
        <Text>This dashboard is only available for parent accounts.</Text>
      </Box>
    );
  }

  return (
    <Box minH="100vh" bg={colorMode === 'dark' ? 'gray.900' : 'gray.50'} p={8}>
      <VStack spacing={6} align="stretch">
        <Flex justify="space-between" align="center">
          <Heading size="lg">Parent Dashboard</Heading>
          <Button leftIcon={<FaPlus />} colorScheme="blue" onClick={onOpen}>
            Add Child Account
          </Button>
        </Flex>

        {/* Children Overview Grid */}
        <Grid templateColumns="repeat(auto-fill, minmax(350px, 1fr))" gap={6}>
          {children.map((child) => {
            const stats = childStats[child.user_id];

            return (
              <Card
                key={child.user_id}
                borderWidth="2px"
                borderColor={colorMode === 'dark' ? 'gray.700' : 'gray.200'}
                _hover={{ borderColor: 'blue.500', transform: 'translateY(-4px)' }}
                transition="all 0.3s"
                cursor="pointer"
                onClick={() => setSelectedChild(child)}
              >
                <CardHeader>
                  <HStack>
                    <Icon as={FaChild} boxSize={6} color="blue.500" />
                    <VStack align="start" spacing={0} flex={1}>
                      <Heading size="md">{child.name}</Heading>
                      <Text fontSize="sm" color="gray.500">
                        Age {child.age}
                      </Text>
                    </VStack>
                    <Badge colorScheme="purple">{child.credits} credits</Badge>
                  </HStack>
                </CardHeader>

                <CardBody>
                  {stats && (
                    <VStack spacing={4} align="stretch">
                      <Stat>
                        <StatLabel>Questions Answered</StatLabel>
                        <StatNumber>{stats.total_questions}</StatNumber>
                        <StatHelpText>
                          {stats.correct_answers} correct ({(stats.accuracy * 100).toFixed(0)}%
                          accuracy)
                        </StatHelpText>
                      </Stat>

                      <Box>
                        <Flex justify="space-between" mb={2}>
                          <Text fontSize="sm">Skills Progress</Text>
                          <Text fontSize="sm" color="gray.500">
                            {stats.skills_mastered} / {stats.total_skills} mastered
                          </Text>
                        </Flex>
                        <Progress
                          value={(stats.skills_mastered / stats.total_skills) * 100}
                          colorScheme="green"
                          borderRadius="full"
                        />
                      </Box>

                      <HStack spacing={4} fontSize="sm" color="gray.600">
                        <HStack>
                          <Icon as={FaTrophy} color="yellow.500" />
                          <Text>{stats.skills_mastered} mastered</Text>
                        </HStack>
                        <HStack>
                          <Icon as={FaClock} color="blue.500" />
                          <Text>{stats.avg_response_time}s avg</Text>
                        </HStack>
                      </HStack>
                    </VStack>
                  )}
                </CardBody>
              </Card>
            );
          })}
        </Grid>

        {children.length === 0 && !loading && (
          <Card p={12} textAlign="center">
            <VStack spacing={4}>
              <Icon as={FaChild} boxSize={16} color="gray.400" />
              <Heading size="md" color="gray.500">
                No child accounts yet
              </Heading>
              <Text color="gray.500">
                Create a child account to start tracking their learning progress
              </Text>
              <Button colorScheme="blue" onClick={onOpen}>
                Add First Child
              </Button>
            </VStack>
          </Card>
        )}
      </VStack>

      {/* Create Child Modal */}
      <Modal isOpen={isOpen} onClose={onClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Create Child Account</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Child's Name</FormLabel>
                <Input
                  value={childName}
                  onChange={(e) => setChildName(e.target.value)}
                  placeholder="Enter name"
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Age</FormLabel>
                <Input
                  type="number"
                  value={childAge}
                  onChange={(e) => setChildAge(e.target.value)}
                  placeholder="Enter age"
                />
              </FormControl>

              <Button colorScheme="blue" w="full" onClick={handleCreateChild}>
                Create Account
              </Button>
            </VStack>
          </ModalBody>
        </ModalContent>
      </Modal>
    </Box>
  );
}
