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
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  useDisclosure,
  Icon,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Grid,
  GridItem,
} from '@chakra-ui/react';
import { FaUser, FaKey, FaGlobe, FaTrash, FaChild, FaCoins } from 'react-icons/fa';
import { useAuth } from '../contexts/AuthContext';
import { useHistory } from 'react-router-dom';

export function AccountManagement() {
  const { user, token, logout, refreshUser } = useAuth();
  const toast = useToast();
  const history = useHistory();
  const { isOpen: isDeleteOpen, onOpen: onDeleteOpen, onClose: onDeleteClose } = useDisclosure();

  // Form states
  const [name, setName] = useState(user?.name || '');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [language, setLanguage] = useState(user?.language || 'en');
  const [region, setRegion] = useState(user?.region || 'US');
  const [loading, setLoading] = useState(false);

  const handleUpdateProfile = async () => {
    if (!token || !user) return;

    setLoading(true);
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
        toast({
          title: 'Profile updated',
          status: 'success',
          duration: 3000,
        });
      } else {
        throw new Error('Failed to update profile');
      }
    } catch (error: any) {
      toast({
        title: 'Update failed',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      toast({
        title: 'Passwords do not match',
        status: 'error',
        duration: 3000,
      });
      return;
    }

    if (newPassword.length < 8) {
      toast({
        title: 'Password must be at least 8 characters',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    setLoading(true);
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
        toast({
          title: 'Password changed successfully',
          status: 'success',
          duration: 3000,
        });
      } else {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to change password');
      }
    } catch (error: any) {
      toast({
        title: 'Password change failed',
        description: error.message,
        status: 'error',
        duration: 5000,
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
          description: 'Your account has been permanently deleted',
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
        <Text>Please log in to access account management.</Text>
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
              Account Management
            </Heading>
            <Button
              onClick={() => history.push('/')}
              variant="outline"
              colorScheme="yellow"
            >
              Back to Home
            </Button>
          </HStack>

          {/* Account Overview */}
          <Grid templateColumns="repeat(auto-fit, minmax(250px, 1fr))" gap={6}>
            <Card bg="gray.900" borderColor="gray.700" borderWidth="1px">
              <CardBody>
                <Stat>
                  <StatLabel color="gray.400">Credits Balance</StatLabel>
                  <StatNumber color="yellow.400">
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
                    <Badge colorScheme="yellow" fontSize="lg">
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
                <Icon as={FaUser} color="yellow.400" boxSize={5} />
                <Heading size="md">Profile Information</Heading>
              </HStack>
            </CardHeader>
            <CardBody>
              <VStack spacing={4} align="stretch">
                <HStack spacing={4}>
                  <Avatar
                    size="xl"
                    name={user.name}
                    src={user.profile_picture}
                    bg="yellow.600"
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
                    <FormLabel color="gray.300">Name</FormLabel>
                    <Input
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      bg="black"
                      borderColor="gray.600"
                      _hover={{ borderColor: 'gray.500' }}
                    />
                  </FormControl>

                  <FormControl>
                    <FormLabel color="gray.300">Email</FormLabel>
                    <Input
                      value={user.email}
                      isReadOnly
                      bg="gray.800"
                      borderColor="gray.600"
                      color="gray.500"
                    />
                  </FormControl>

                  <FormControl>
                    <FormLabel color="gray.300">Language</FormLabel>
                    <Select
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      bg="black"
                      borderColor="gray.600"
                    >
                      <option value="en" style={{ background: 'black' }}>English</option>
                      <option value="es" style={{ background: 'black' }}>Spanish</option>
                      <option value="fr" style={{ background: 'black' }}>French</option>
                      <option value="de" style={{ background: 'black' }}>German</option>
                      <option value="zh" style={{ background: 'black' }}>Chinese</option>
                      <option value="ja" style={{ background: 'black' }}>Japanese</option>
                    </Select>
                  </FormControl>

                  <FormControl>
                    <FormLabel color="gray.300">Region</FormLabel>
                    <Select
                      value={region}
                      onChange={(e) => setRegion(e.target.value)}
                      bg="black"
                      borderColor="gray.600"
                    >
                      <option value="US" style={{ background: 'black' }}>United States</option>
                      <option value="GB" style={{ background: 'black' }}>United Kingdom</option>
                      <option value="CA" style={{ background: 'black' }}>Canada</option>
                      <option value="AU" style={{ background: 'black' }}>Australia</option>
                      <option value="IN" style={{ background: 'black' }}>India</option>
                      <option value="EU" style={{ background: 'black' }}>Europe</option>
                    </Select>
                  </FormControl>
                </Grid>

                <Button
                  colorScheme="yellow"
                  onClick={handleUpdateProfile}
                  isLoading={loading}
                  alignSelf="start"
                >
                  Save Changes
                </Button>
              </VStack>
            </CardBody>
          </Card>

          {/* Change Password */}
          {user.auth_provider === 'email' && (
            <Card bg="gray.900" borderColor="gray.700" borderWidth="1px">
              <CardHeader>
                <HStack>
                  <Icon as={FaKey} color="yellow.400" boxSize={5} />
                  <Heading size="md">Change Password</Heading>
                </HStack>
              </CardHeader>
              <CardBody>
                <VStack spacing={4} align="stretch">
                  <FormControl>
                    <FormLabel color="gray.300">Current Password</FormLabel>
                    <Input
                      type="password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      bg="black"
                      borderColor="gray.600"
                      placeholder="Enter current password"
                    />
                  </FormControl>

                  <FormControl>
                    <FormLabel color="gray.300">New Password</FormLabel>
                    <Input
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      bg="black"
                      borderColor="gray.600"
                      placeholder="Enter new password (min 8 characters)"
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
                      placeholder="Confirm new password"
                    />
                  </FormControl>

                  <Button
                    colorScheme="yellow"
                    onClick={handleChangePassword}
                    isLoading={loading}
                    isDisabled={!currentPassword || !newPassword || !confirmPassword}
                    alignSelf="start"
                  >
                    Change Password
                  </Button>
                </VStack>
              </CardBody>
            </Card>
          )}

          {/* Danger Zone */}
          <Card bg="red.900" borderColor="red.700" borderWidth="2px">
            <CardHeader>
              <HStack>
                <Icon as={FaTrash} color="red.400" boxSize={5} />
                <Heading size="md" color="red.300">
                  Danger Zone
                </Heading>
              </HStack>
            </CardHeader>
            <CardBody>
              <VStack spacing={4} align="stretch">
                <Text color="red.200">
                  Once you delete your account, there is no going back. Please be certain.
                </Text>
                <Button
                  colorScheme="red"
                  onClick={onDeleteOpen}
                  alignSelf="start"
                >
                  Delete Account
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
            >
              Terms of Service
            </Button>
            <Text color="gray.600">•</Text>
            <Button
              variant="link"
              color="yellow.400"
              onClick={() => history.push('/privacy-policy')}
            >
              Privacy Policy
            </Button>
          </HStack>
        </VStack>
      </Container>

      {/* Delete Confirmation Modal */}
      <Modal isOpen={isDeleteOpen} onClose={onDeleteClose}>
        <ModalOverlay />
        <ModalContent bg="gray.900" color="white">
          <ModalHeader>Confirm Account Deletion</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4} align="stretch">
              <Text>
                Are you sure you want to delete your account? This action cannot be undone.
              </Text>
              <Text color="red.400" fontWeight="bold">
                All your data, including:
              </Text>
              <VStack align="start" pl={4} spacing={1}>
                <Text>• Learning progress and skill mastery</Text>
                <Text>• Question history and conversations</Text>
                <Text>• Remaining credits</Text>
                {user.account_type === 'parent' && (
                  <Text>• All child accounts will also be deleted</Text>
                )}
              </VStack>
              <Text fontWeight="bold">This data will be permanently deleted.</Text>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onDeleteClose}>
              Cancel
            </Button>
            <Button
              colorScheme="red"
              onClick={handleDeleteAccount}
              isLoading={loading}
            >
              Yes, Delete My Account
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
}
