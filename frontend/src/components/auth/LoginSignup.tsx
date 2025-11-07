import { useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  VStack,
  Heading,
  Text,
  Tab,
  Tabs,
  TabList,
  TabPanel,
  TabPanels,
  useToast,
  Divider,
  HStack,
  Icon,
} from '@chakra-ui/react';
import { FaGoogle, FaApple, FaFacebook } from 'react-icons/fa';
import { useAuth } from '../../contexts/AuthContext';

export function LoginSignup() {
  const { login, signup, googleLogin } = useAuth();
  const toast = useToast();

  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  const [signupName, setSignupName] = useState('');
  const [signupAge, setSignupAge] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await login(loginEmail, loginPassword);
      toast({
        title: 'Login successful!',
        status: 'success',
        duration: 3000,
      });
    } catch (error: any) {
      toast({
        title: 'Login failed',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await signup(signupEmail, signupPassword, signupName, signupAge ? parseInt(signupAge) : undefined);
      toast({
        title: 'Account created successfully!',
        status: 'success',
        duration: 3000,
      });
    } catch (error: any) {
      toast({
        title: 'Signup failed',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box minH="100vh" display="flex" alignItems="center" justifyContent="center" bg="black" p={4}>
      <Box maxW="md" w="full" bg="gray.900" borderRadius="xl" boxShadow="xl" p={8} borderWidth="1px" borderColor="gray.700">
        <Heading size="lg" mb={2} textAlign="center" color="yellow.400">
          AI Tutor
        </Heading>
        <Text textAlign="center" color="gray.400" mb={6}>
          Your Personalized Learning Journey
        </Text>

        <Tabs isFitted variant="enclosed">
          <TabList mb={4}>
            <Tab>Login</Tab>
            <Tab>Sign Up</Tab>
          </TabList>

          <TabPanels>
            {/* Login Panel */}
            <TabPanel>
              <VStack as="form" onSubmit={handleLogin} spacing={4}>
                <FormControl isRequired>
                  <FormLabel>Email</FormLabel>
                  <Input
                    type="email"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    placeholder="your@email.com"
                  />
                </FormControl>

                <FormControl isRequired>
                  <FormLabel>Password</FormLabel>
                  <Input
                    type="password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    placeholder="••••••••"
                  />
                </FormControl>

                <Button
                  type="submit"
                  colorScheme="yellow"
                  w="full"
                  isLoading={loading}
                >
                  Login
                </Button>

                <Divider />

                <Text fontSize="sm" color="gray.600">
                  Or continue with
                </Text>

                <VStack w="full" spacing={2}>
                  <Button
                    leftIcon={<Icon as={FaGoogle} />}
                    variant="outline"
                    w="full"
                    onClick={() => {
                      toast({
                        title: 'Google OAuth',
                        description: 'Integrate with Google OAuth in production',
                        status: 'info',
                      });
                    }}
                  >
                    Google
                  </Button>

                  <HStack w="full" spacing={2}>
                    <Button
                      leftIcon={<Icon as={FaApple} />}
                      variant="outline"
                      flex={1}
                      onClick={() => {
                        toast({
                          title: 'Apple OAuth',
                          description: 'Integrate with Apple Sign In',
                          status: 'info',
                        });
                      }}
                    >
                      Apple
                    </Button>

                    <Button
                      leftIcon={<Icon as={FaFacebook} />}
                      variant="outline"
                      flex={1}
                      onClick={() => {
                        toast({
                          title: 'Facebook OAuth',
                          description: 'Integrate with Facebook Login',
                          status: 'info',
                        });
                      }}
                    >
                      Facebook
                    </Button>
                  </HStack>
                </VStack>
              </VStack>
            </TabPanel>

            {/* Signup Panel */}
            <TabPanel>
              <VStack as="form" onSubmit={handleSignup} spacing={4}>
                <FormControl isRequired>
                  <FormLabel>Name</FormLabel>
                  <Input
                    value={signupName}
                    onChange={(e) => setSignupName(e.target.value)}
                    placeholder="John Doe"
                  />
                </FormControl>

                <FormControl isRequired>
                  <FormLabel>Email</FormLabel>
                  <Input
                    type="email"
                    value={signupEmail}
                    onChange={(e) => setSignupEmail(e.target.value)}
                    placeholder="your@email.com"
                  />
                </FormControl>

                <FormControl isRequired>
                  <FormLabel>Password</FormLabel>
                  <Input
                    type="password"
                    value={signupPassword}
                    onChange={(e) => setSignupPassword(e.target.value)}
                    placeholder="••••••••"
                  />
                </FormControl>

                <FormControl>
                  <FormLabel>Age (optional)</FormLabel>
                  <Input
                    type="number"
                    value={signupAge}
                    onChange={(e) => setSignupAge(e.target.value)}
                    placeholder="18"
                  />
                </FormControl>

                <Button
                  type="submit"
                  colorScheme="yellow"
                  w="full"
                  isLoading={loading}
                >
                  Create Account
                </Button>
              </VStack>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </Box>
    </Box>
  );
}
