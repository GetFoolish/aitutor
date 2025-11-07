import { useState } from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Button,
  FormControl,
  FormLabel,
  Input,
  Select,
  Card,
  CardHeader,
  CardBody,
  Avatar,
  Badge,
  Divider,
  useToast,
  Icon,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Grid,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
} from '@chakra-ui/react';
import { FaUser, FaGlobe, FaChild, FaCoins, FaCheck } from 'react-icons/fa';
import { useAuth } from '../contexts/AuthContext';
import { useHistory } from 'react-router-dom';

export function ProfilePage() {
  const { user, token, refreshUser } = useAuth();
  const toast = useToast();
  const history = useHistory();

  // Form states
  const [name, setName] = useState(user?.name || '');
  const [language, setLanguage] = useState(user?.language || 'en');
  const [region, setRegion] = useState(user?.region || detectUserRegion());
  const [loading, setLoading] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Auto-detect region based on browser locale
  function detectUserRegion(): string {
    const locale = navigator.language || 'en-US';
    const regionCode = locale.split('-')[1] || 'US';

    // Map common regions
    const regionMap: Record<string, string> = {
      'US': 'US',
      'GB': 'GB',
      'CA': 'CA',
      'AU': 'AU',
      'IN': 'IN',
    };

    return regionMap[regionCode] || 'US';
  }

  const handleUpdateProfile = async () => {
    if (!token || !user) return;

    setLoading(true);
    setSaveSuccess(false);

    try {
      const response = await fetch(`http://localhost:8001/auth/user/${user.user_id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name,
          language,
          region,
        }),
      });

      if (response.ok) {
        await refreshUser();
        setSaveSuccess(true);
        toast({
          title: 'Profile updated successfully!',
          description: 'Your changes have been saved.',
          status: 'success',
          duration: 4000,
          isClosable: true,
          position: 'top',
        });

        // Hide success message after 3 seconds
        setTimeout(() => setSaveSuccess(false), 3000);
      } else {
        throw new Error('Failed to update profile');
      }
    } catch (error: any) {
      toast({
        title: 'Update failed',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return (
      <Box minH="100vh" bg="black" color="white" p={8}>
        <Text>Please log in to access your profile.</Text>
      </Box>
    );
  }

  return (
    <Box minH="100vh" bg="black" color="white" py={8}>
      <Container maxW="6xl">
        <VStack spacing={8} align="stretch">
          {/* Header */}
          <HStack justify="space-between">
            <Heading size="xl" color="purple.400">
              My Profile
            </Heading>
            <Button
              onClick={() => history.push('/')}
              variant="solid"
              bg="gray.800"
              color="white"
              _hover={{ bg: 'gray.700' }}
              borderWidth="1px"
              borderColor="gray.600"
            >
              Back to Home
            </Button>
          </HStack>

          {/* Save Success Alert */}
          {saveSuccess && (
            <Alert status="success" bg="green.900" borderRadius="md" borderWidth="1px" borderColor="green.600">
              <AlertIcon as={FaCheck} color="green.400" />
              <VStack align="start" spacing={0}>
                <AlertTitle color="green.300">Changes saved!</AlertTitle>
                <AlertDescription color="green.200">Your profile has been updated successfully.</AlertDescription>
              </VStack>
            </Alert>
          )}

          {/* Account Overview */}
          <Grid templateColumns="repeat(auto-fit, minmax(250px, 1fr))" gap={6}>
            <Card bg="gray.900" borderColor="gray.700" borderWidth="1px">
              <CardBody>
                <Stat>
                  <StatLabel color="gray.400">Credits Balance</StatLabel>
                  <StatNumber color="purple.400">
                    <Icon as={FaCoins} mr={2} />
                    {user.credits}
                  </StatNumber>
                  <StatHelpText color="gray.500">Available for use</StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg="gray.900" borderColor="gray.700" borderWidth="1px">
              <CardBody>
                <Stat>
                  <StatLabel color="gray.400">Account Type</StatLabel>
                  <StatNumber>
                    <Badge colorScheme="purple" fontSize="lg">
                      {user.account_type}
                    </Badge>
                  </StatNumber>
                  <StatHelpText color="gray.500">
                    {user.account_type === 'parent' ? 'Parent Account' : 'Student Account'}
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            {user.account_type === 'parent' && (
              <Card bg="gray.900" borderColor="gray.700" borderWidth="1px">
                <CardBody>
                  <Stat>
                    <StatLabel color="gray.400">Child Accounts</StatLabel>
                    <StatNumber color="white">
                      <Icon as={FaChild} mr={2} />
                      {user.children?.length || 0}
                    </StatNumber>
                    <StatHelpText color="gray.500">Managed accounts</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>
            )}
          </Grid>

          {/* Profile Information */}
          <Card bg="gray.900" borderColor="gray.700" borderWidth="1px">
            <CardHeader>
              <HStack>
                <Icon as={FaUser} color="purple.400" boxSize={5} />
                <Heading size="md">Personal Information</Heading>
              </HStack>
            </CardHeader>
            <CardBody>
              <VStack spacing={6} align="stretch">
                <HStack spacing={4}>
                  <Avatar
                    size="xl"
                    name={user.name}
                    src={user.profile_picture}
                    bg="purple.600"
                  />
                  <VStack align="start" spacing={1}>
                    <Text fontSize="xl" fontWeight="bold">
                      {user.name}
                    </Text>
                    <Text color="gray.400">{user.email}</Text>
                    <Badge colorScheme="purple">
                      {user.auth_provider}
                    </Badge>
                  </VStack>
                </HStack>

                <Divider borderColor="gray.700" />

                <Grid templateColumns="repeat(auto-fit, minmax(300px, 1fr))" gap={4}>
                  <FormControl>
                    <FormLabel color="gray.300">Display Name</FormLabel>
                    <Input
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      bg="black"
                      borderColor="gray.600"
                      _hover={{ borderColor: 'purple.500' }}
                      _focus={{ borderColor: 'purple.400', boxShadow: '0 0 0 1px var(--chakra-colors-purple-400)' }}
                      placeholder="Enter your name"
                    />
                  </FormControl>

                  <FormControl>
                    <FormLabel color="gray.300">Email Address</FormLabel>
                    <Input
                      value={user.email}
                      isReadOnly
                      bg="gray.800"
                      borderColor="gray.600"
                      color="gray.500"
                      cursor="not-allowed"
                    />
                    <Text fontSize="xs" color="gray.500" mt={1}>
                      Email cannot be changed
                    </Text>
                  </FormControl>

                  <FormControl>
                    <FormLabel color="gray.300">
                      <HStack spacing={1}>
                        <Icon as={FaGlobe} boxSize={3} />
                        <span>Preferred Language</span>
                      </HStack>
                    </FormLabel>
                    <Select
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      bg="black"
                      borderColor="gray.600"
                      _hover={{ borderColor: 'purple.500' }}
                      _focus={{ borderColor: 'purple.400', boxShadow: '0 0 0 1px var(--chakra-colors-purple-400)' }}
                    >
                      <option value="en" style={{ background: 'black' }}>English</option>
                      <option value="es" style={{ background: 'black' }}>Español</option>
                      <option value="fr" style={{ background: 'black' }}>Français</option>
                      <option value="de" style={{ background: 'black' }}>Deutsch</option>
                      <option value="zh" style={{ background: 'black' }}>中文</option>
                      <option value="ja" style={{ background: 'black' }}>日本語</option>
                    </Select>
                  </FormControl>

                  <FormControl>
                    <FormLabel color="gray.300">
                      <HStack spacing={1}>
                        <Icon as={FaGlobe} boxSize={3} />
                        <span>Region</span>
                      </HStack>
                    </FormLabel>
                    <Select
                      value={region}
                      onChange={(e) => setRegion(e.target.value)}
                      bg="black"
                      borderColor="gray.600"
                      _hover={{ borderColor: 'purple.500' }}
                      _focus={{ borderColor: 'purple.400', boxShadow: '0 0 0 1px var(--chakra-colors-purple-400)' }}
                    >
                      <option value="US" style={{ background: 'black' }}>🇺🇸 United States</option>
                      <option value="CA" style={{ background: 'black' }}>🇨🇦 Canada</option>
                      <option value="GB" style={{ background: 'black' }}>🇬🇧 United Kingdom</option>
                      <option value="AU" style={{ background: 'black' }}>🇦🇺 Australia</option>
                      <option value="IN" style={{ background: 'black' }}>🇮🇳 India</option>
                      <option value="EU" style={{ background: 'black' }}>🇪🇺 Europe</option>
                    </Select>
                    <Text fontSize="xs" color="gray.500" mt={1}>
                      Affects content recommendations and localization
                    </Text>
                  </FormControl>
                </Grid>

                <HStack spacing={3}>
                  <Button
                    colorScheme="purple"
                    onClick={handleUpdateProfile}
                    isLoading={loading}
                    loadingText="Saving..."
                    size="lg"
                    leftIcon={<FaCheck />}
                    _hover={{ transform: 'translateY(-1px)', boxShadow: 'lg' }}
                    transition="all 0.2s"
                  >
                    Save Changes
                  </Button>
                  {saveSuccess && (
                    <Text color="green.400" fontWeight="semibold" fontSize="sm" animation="fadeIn 0.3s ease-in">
                      ✓ Saved successfully!
                    </Text>
                  )}
                </HStack>
              </VStack>
            </CardBody>
          </Card>

          {/* Footer Links */}
          <HStack justify="center" spacing={6} pt={4}>
            <Button
              variant="link"
              color="purple.400"
              onClick={() => history.push('/terms-of-service')}
              _hover={{ color: 'purple.300' }}
            >
              Terms of Service
            </Button>
            <Text color="gray.600">•</Text>
            <Button
              variant="link"
              color="purple.400"
              onClick={() => history.push('/privacy-policy')}
              _hover={{ color: 'purple.300' }}
            >
              Privacy Policy
            </Button>
          </HStack>
        </VStack>
      </Container>
    </Box>
  );
}
