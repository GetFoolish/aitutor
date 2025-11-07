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
  Card,
  CardHeader,
  CardBody,
  useToast,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  useDisclosure,
  Icon,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Divider,
} from '@chakra-ui/react';
import { FaKey, FaTrash, FaShieldAlt, FaExclamationTriangle, FaCheck } from 'react-icons/fa';
import { useAuth } from '../contexts/AuthContext';
import { useHistory } from 'react-router-dom';

export function SettingsPage() {
  const { user, token, logout } = useAuth();
  const toast = useToast();
  const history = useHistory();
  const { isOpen: isDeleteOpen, onOpen: onDeleteOpen, onClose: onDeleteClose } = useDisclosure();

  // Password change states
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState(false);

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      toast({
        title: 'Passwords do not match',
        description: 'Please make sure both password fields are identical.',
        status: 'error',
        duration: 4000,
        isClosable: true,
      });
      return;
    }

    if (newPassword.length < 8) {
      toast({
        title: 'Password too short',
        description: 'Password must be at least 8 characters long.',
        status: 'warning',
        duration: 4000,
        isClosable: true,
      });
      return;
    }

    setLoading(true);
    setPasswordSuccess(false);

    try {
      const response = await fetch('http://localhost:8001/auth/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      if (response.ok) {
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
        setPasswordSuccess(true);
        toast({
          title: 'Password changed successfully!',
          description: 'Your password has been updated.',
          status: 'success',
          duration: 4000,
          isClosable: true,
          position: 'top',
        });

        // Hide success message after 3 seconds
        setTimeout(() => setPasswordSuccess(false), 3000);
      } else {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to change password');
      }
    } catch (error: any) {
      toast({
        title: 'Password change failed',
        description: error.message || 'Please check your current password and try again.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!token || !user) return;

    setLoading(true);
    try {
      const response = await fetch(`http://localhost:8001/auth/user/${user.user_id}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        toast({
          title: 'Account deleted',
          description: 'Your account has been permanently deleted. Goodbye!',
          status: 'info',
          duration: 5000,
        });
        logout();
        history.push('/');
      } else {
        throw new Error('Failed to delete account');
      }
    } catch (error: any) {
      toast({
        title: 'Deletion failed',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setLoading(false);
      onDeleteClose();
    }
  };

  if (!user) {
    return (
      <Box minH="100vh" bg="black" color="white" p={8}>
        <Text>Please log in to access settings.</Text>
      </Box>
    );
  }

  return (
    <Box minH="100vh" bg="black" color="white" py={8}>
      <Container maxW="6xl">
        <VStack spacing={8} align="stretch">
          {/* Header */}
          <HStack justify="space-between">
            <Heading size="xl" color="yellow.400">
              Account Settings
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

          {/* Password Success Alert */}
          {passwordSuccess && (
            <Alert status="success" bg="green.900" borderRadius="md" borderWidth="1px" borderColor="green.600">
              <AlertIcon as={FaCheck} color="green.400" />
              <VStack align="start" spacing={0}>
                <AlertTitle color="green.300">Password updated!</AlertTitle>
                <AlertDescription color="green.200">Your password has been changed successfully.</AlertDescription>
              </VStack>
            </Alert>
          )}

          {/* Security Section */}
          <Card bg="gray.900" borderColor="gray.700" borderWidth="1px">
            <CardHeader>
              <HStack>
                <Icon as={FaShieldAlt} color="yellow.400" boxSize={5} />
                <Heading size="md">Security & Privacy</Heading>
              </HStack>
            </CardHeader>
            <CardBody>
              <VStack spacing={4} align="stretch">
                <Text color="gray.300" fontSize="sm">
                  Manage your account security settings and authentication preferences.
                </Text>
              </VStack>
            </CardBody>
          </Card>

          {/* Change Password */}
          {user.auth_provider === 'email' ? (
            <Card bg="gray.900" borderColor="gray.700" borderWidth="1px">
              <CardHeader>
                <HStack>
                  <Icon as={FaKey} color="yellow.400" boxSize={5} />
                  <Heading size="md">Change Password</Heading>
                </HStack>
              </CardHeader>
              <CardBody>
                <VStack spacing={4} align="stretch">
                  <Text color="gray.400" fontSize="sm" mb={2}>
                    Choose a strong password that you haven't used elsewhere. Must be at least 8 characters.
                  </Text>

                  <FormControl>
                    <FormLabel color="gray.300">Current Password</FormLabel>
                    <Input
                      type="password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      bg="black"
                      borderColor="gray.600"
                      placeholder="Enter your current password"
                      _hover={{ borderColor: 'yellow.500' }}
                      _focus={{ borderColor: 'yellow.400', boxShadow: '0 0 0 1px var(--chakra-colors-yellow-400)' }}
                    />
                  </FormControl>

                  <Divider borderColor="gray.700" />

                  <FormControl>
                    <FormLabel color="gray.300">New Password</FormLabel>
                    <Input
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      bg="black"
                      borderColor="gray.600"
                      placeholder="Enter new password (min 8 characters)"
                      _hover={{ borderColor: 'yellow.500' }}
                      _focus={{ borderColor: 'yellow.400', boxShadow: '0 0 0 1px var(--chakra-colors-yellow-400)' }}
                    />
                  </FormControl>

                  <FormControl>
                    <FormLabel color="gray.300">Confirm New Password</FormLabel>
                    <Input
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      bg="black"
                      borderColor="gray.600"
                      placeholder="Re-enter your new password"
                      _hover={{ borderColor: 'yellow.500' }}
                      _focus={{ borderColor: 'yellow.400', boxShadow: '0 0 0 1px var(--chakra-colors-yellow-400)' }}
                    />
                  </FormControl>

                  <HStack spacing={3}>
                    <Button
                      colorScheme="yellow"
                      onClick={handleChangePassword}
                      isLoading={loading}
                      loadingText="Updating..."
                      isDisabled={!currentPassword || !newPassword || !confirmPassword}
                      size="lg"
                      leftIcon={<FaKey />}
                      _hover={{ transform: 'translateY(-1px)', boxShadow: 'lg' }}
                      transition="all 0.2s"
                    >
                      Update Password
                    </Button>
                    {passwordSuccess && (
                      <Text color="green.400" fontWeight="semibold" fontSize="sm">
                        ✓ Updated successfully!
                      </Text>
                    )}
                  </HStack>
                </VStack>
              </CardBody>
            </Card>
          ) : (
            <Card bg="gray.900" borderColor="gray.700" borderWidth="1px">
              <CardBody>
                <VStack spacing={2} align="start">
                  <HStack>
                    <Icon as={FaKey} color="gray.500" boxSize={5} />
                    <Heading size="md" color="gray.500">Password Settings</Heading>
                  </HStack>
                  <Text color="gray.500">
                    You're signed in with <strong>{user.auth_provider}</strong>. Password management is not available for OAuth accounts.
                  </Text>
                </VStack>
              </CardBody>
            </Card>
          )}

          {/* Danger Zone */}
          <Card bg="red.900" borderColor="red.700" borderWidth="2px">
            <CardHeader>
              <HStack>
                <Icon as={FaExclamationTriangle} color="red.400" boxSize={5} />
                <Heading size="md" color="red.300">
                  Danger Zone
                </Heading>
              </HStack>
            </CardHeader>
            <CardBody>
              <VStack spacing={4} align="stretch">
                <Alert status="warning" bg="red.950" borderRadius="md">
                  <AlertIcon color="red.400" />
                  <VStack align="start" spacing={1}>
                    <AlertTitle color="red.300">Irreversible Action</AlertTitle>
                    <AlertDescription color="red.200">
                      Once you delete your account, there is no going back. All your data will be permanently erased.
                    </AlertDescription>
                  </VStack>
                </Alert>

                <Button
                  colorScheme="red"
                  onClick={onDeleteOpen}
                  alignSelf="start"
                  leftIcon={<FaTrash />}
                  size="lg"
                  _hover={{ transform: 'translateY(-1px)', boxShadow: 'lg' }}
                  transition="all 0.2s"
                >
                  Delete My Account
                </Button>
              </VStack>
            </CardBody>
          </Card>

          {/* Footer Links */}
          <HStack justify="center" spacing={6} pt={4}>
            <Button
              variant="link"
              color="yellow.400"
              onClick={() => history.push('/terms-of-service')}
              _hover={{ color: 'yellow.300' }}
            >
              Terms of Service
            </Button>
            <Text color="gray.600">•</Text>
            <Button
              variant="link"
              color="yellow.400"
              onClick={() => history.push('/privacy-policy')}
              _hover={{ color: 'yellow.300' }}
            >
              Privacy Policy
            </Button>
          </HStack>
        </VStack>
      </Container>

      {/* Delete Confirmation Modal */}
      <Modal isOpen={isDeleteOpen} onClose={onDeleteClose} isCentered>
        <ModalOverlay bg="blackAlpha.800" backdropFilter="blur(4px)" />
        <ModalContent bg="gray.900" color="white" borderWidth="2px" borderColor="red.600">
          <ModalHeader color="red.400">
            <HStack>
              <Icon as={FaExclamationTriangle} />
              <Text>Confirm Account Deletion</Text>
            </HStack>
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4} align="stretch">
              <Alert status="error" bg="red.950" borderRadius="md">
                <AlertIcon />
                <Text fontWeight="bold">This action cannot be undone!</Text>
              </Alert>

              <Text>
                Are you absolutely sure you want to delete your account? You will lose:
              </Text>

              <VStack align="start" pl={4} spacing={2} color="gray.300">
                <Text>• All learning progress and skill mastery</Text>
                <Text>• Question history and conversations</Text>
                <Text>• {user.credits} remaining credits</Text>
                {user.account_type === 'parent' && (
                  <Text color="red.400" fontWeight="bold">
                    • All {user.children?.length || 0} child account(s) will also be deleted
                  </Text>
                )}
              </VStack>

              <Text fontWeight="bold" color="red.400">
                This data will be permanently erased and cannot be recovered.
              </Text>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button
              variant="ghost"
              mr={3}
              onClick={onDeleteClose}
              _hover={{ bg: 'gray.800' }}
            >
              Cancel
            </Button>
            <Button
              colorScheme="red"
              onClick={handleDeleteAccount}
              isLoading={loading}
              loadingText="Deleting..."
              leftIcon={<FaTrash />}
            >
              Yes, Delete Forever
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
}
