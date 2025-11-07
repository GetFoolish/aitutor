import { useEffect, useState } from 'react';
import {
  Box,
  Container,
  VStack,
  Heading,
  Text,
  Button,
  Icon,
  Spinner,
  HStack,
  Card,
  CardBody,
  chakra,
} from '@chakra-ui/react';
import { FaCheckCircle, FaCoins } from 'react-icons/fa';
import { useHistory, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { motion } from 'framer-motion';

const MotionBox = chakra(motion.div);

export function PaymentSuccess() {
  const history = useHistory();
  const location = useLocation();
  const { user, refreshUser } = useAuth();
  const [loading, setLoading] = useState(true);
  const [paymentDetails, setPaymentDetails] = useState<any>(null);

  const searchParams = new URLSearchParams(location.search);
  const sessionId = searchParams.get('session_id');

  useEffect(() => {
    // Refresh user data to get updated credits
    const fetchUpdatedData = async () => {
      if (user) {
        await refreshUser();
        setLoading(false);

        // Optional: Fetch payment session details from your backend
        // This would show which package was purchased
        if (sessionId) {
          // You can implement an endpoint to retrieve session details
          // For now, we'll just show a success message
        }
      }
    };

    const timer = setTimeout(() => {
      fetchUpdatedData();
    }, 2000); // Small delay to ensure webhook has processed

    return () => clearTimeout(timer);
  }, [user, sessionId]);

  if (loading) {
    return (
      <Box
        minH="100vh"
        bg="black"
        color="white"
        display="flex"
        alignItems="center"
        justifyContent="center"
      >
        <VStack spacing={4}>
          <Spinner size="xl" color="yellow.400" />
          <Text color="gray.400">Processing your payment...</Text>
        </VStack>
      </Box>
    );
  }

  return (
    <Box minH="100vh" bg="black" color="white" py={12}>
      <Container maxW="2xl">
        <VStack spacing={8}>
          {/* Success Animation */}
          <MotionBox
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.5, type: 'spring' }}
          >
            <Box
              position="relative"
              w="120px"
              h="120px"
              borderRadius="full"
              bg="green.900"
              display="flex"
              alignItems="center"
              justifyContent="center"
            >
              <Icon as={FaCheckCircle} boxSize={16} color="green.400" />
            </Box>
          </MotionBox>

          {/* Success Message */}
          <VStack spacing={4} textAlign="center">
            <Heading size="2xl" color="yellow.400">
              Payment Successful!
            </Heading>
            <Text fontSize="lg" color="gray.300">
              Thank you for your purchase. Your credits have been added to your account.
            </Text>
          </VStack>

          {/* Credits Card */}
          <Card
            bg="gray.900"
            borderColor="yellow.600"
            borderWidth="2px"
            w="full"
          >
            <CardBody>
              <VStack spacing={4}>
                <HStack spacing={3}>
                  <Icon as={FaCoins} boxSize={8} color="yellow.400" />
                  <VStack align="start" spacing={0}>
                    <Text fontSize="sm" color="gray.400">
                      Your New Balance
                    </Text>
                    <Heading size="xl" color="yellow.400">
                      {user?.credits || 0} Credits
                    </Heading>
                  </VStack>
                </HStack>

                <Text fontSize="sm" color="gray.400" textAlign="center">
                  Your credits are ready to use for AI tutoring sessions!
                </Text>
              </VStack>
            </CardBody>
          </Card>

          {/* Receipt Information */}
          <Card bg="gray.900" borderColor="gray.700" borderWidth="1px" w="full">
            <CardBody>
              <VStack spacing={3} align="stretch">
                <Heading size="sm" color="gray.300">
                  Payment Details
                </Heading>
                <HStack justify="space-between">
                  <Text color="gray.400" fontSize="sm">
                    Payment Method
                  </Text>
                  <Text color="white" fontSize="sm">
                    Card Payment
                  </Text>
                </HStack>
                <HStack justify="space-between">
                  <Text color="gray.400" fontSize="sm">
                    Status
                  </Text>
                  <Text color="green.400" fontSize="sm" fontWeight="bold">
                    Completed
                  </Text>
                </HStack>
                {sessionId && (
                  <HStack justify="space-between">
                    <Text color="gray.400" fontSize="sm">
                      Transaction ID
                    </Text>
                    <Text color="white" fontSize="xs" fontFamily="mono">
                      {sessionId.substring(0, 20)}...
                    </Text>
                  </HStack>
                )}
                <Text fontSize="xs" color="gray.500" pt={2}>
                  A receipt has been sent to your email address.
                </Text>
              </VStack>
            </CardBody>
          </Card>

          {/* Action Buttons */}
          <VStack spacing={3} w="full">
            <Button
              colorScheme="yellow"
              size="lg"
              w="full"
              onClick={() => history.push('/')}
            >
              Start Learning
            </Button>
            <Button
              variant="outline"
              colorScheme="yellow"
              size="md"
              w="full"
              onClick={() => history.push('/account')}
            >
              View Account
            </Button>
          </VStack>

          {/* Support Link */}
          <Text fontSize="sm" color="gray.500" textAlign="center">
            Need help? Contact us at{' '}
            <Text as="span" color="yellow.400">
              support@aitutor.com
            </Text>
          </Text>
        </VStack>
      </Container>
    </Box>
  );
}
