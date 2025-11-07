import {
  Box,
  Container,
  VStack,
  Heading,
  Text,
  Button,
  Icon,
  HStack,
  Card,
  CardBody,
  Divider,
  chakra,
} from '@chakra-ui/react';
import { FaTimesCircle, FaCoins, FaQuestionCircle } from 'react-icons/fa';
import { useHistory } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { motion } from 'framer-motion';

const MotionBox = chakra(motion.div);

export function PaymentCancel() {
  const history = useHistory();
  const { user } = useAuth();

  return (
    <Box minH="100vh" bg="black" color="white" py={12}>
      <Container maxW="2xl">
        <VStack spacing={8}>
          {/* Cancel Icon */}
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
              bg="orange.900"
              display="flex"
              alignItems="center"
              justifyContent="center"
            >
              <Icon as={FaTimesCircle} boxSize={16} color="orange.400" />
            </Box>
          </MotionBox>

          {/* Message */}
          <VStack spacing={4} textAlign="center">
            <Heading size="2xl" color="orange.400">
              Payment Cancelled
            </Heading>
            <Text fontSize="lg" color="gray.300">
              Your payment was not completed. No charges have been made to your account.
            </Text>
          </VStack>

          {/* Current Balance */}
          <Card
            bg="gray.900"
            borderColor="gray.700"
            borderWidth="1px"
            w="full"
          >
            <CardBody>
              <VStack spacing={3}>
                <HStack spacing={3}>
                  <Icon as={FaCoins} boxSize={6} color="yellow.400" />
                  <VStack align="start" spacing={0}>
                    <Text fontSize="sm" color="gray.400">
                      Your Current Balance
                    </Text>
                    <Heading size="lg" color="yellow.400">
                      {user?.credits || 0} Credits
                    </Heading>
                  </VStack>
                </HStack>
              </VStack>
            </CardBody>
          </Card>

          {/* Why might payment fail */}
          <Card bg="gray.900" borderColor="gray.700" borderWidth="1px" w="full">
            <CardBody>
              <VStack spacing={4} align="stretch">
                <HStack>
                  <Icon as={FaQuestionCircle} color="yellow.400" boxSize={5} />
                  <Heading size="sm" color="gray.300">
                    Why was my payment cancelled?
                  </Heading>
                </HStack>

                <Text fontSize="sm" color="gray.400">
                  Common reasons include:
                </Text>

                <VStack align="start" spacing={2} pl={4}>
                  <HStack>
                    <Box w="6px" h="6px" borderRadius="full" bg="yellow.400" />
                    <Text fontSize="sm" color="gray.400">
                      You clicked the back button or closed the payment window
                    </Text>
                  </HStack>
                  <HStack>
                    <Box w="6px" h="6px" borderRadius="full" bg="yellow.400" />
                    <Text fontSize="sm" color="gray.400">
                      You decided to review the purchase later
                    </Text>
                  </HStack>
                  <HStack>
                    <Box w="6px" h="6px" borderRadius="full" bg="yellow.400" />
                    <Text fontSize="sm" color="gray.400">
                      You wanted to choose a different payment method
                    </Text>
                  </HStack>
                  <HStack>
                    <Box w="6px" h="6px" borderRadius="full" bg="yellow.400" />
                    <Text fontSize="sm" color="gray.400">
                      Your session timed out
                    </Text>
                  </HStack>
                </VStack>

                <Divider borderColor="gray.700" />

                <Text fontSize="sm" color="gray.400">
                  Don't worry! You can try again anytime, and we're here to help if you need
                  assistance.
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
              leftIcon={<FaCoins />}
            >
              Try Again - Buy Credits
            </Button>

            <HStack w="full" spacing={3}>
              <Button
                variant="outline"
                colorScheme="yellow"
                size="md"
                flex={1}
                onClick={() => history.push('/')}
              >
                Continue Learning
              </Button>
              <Button
                variant="outline"
                colorScheme="yellow"
                size="md"
                flex={1}
                onClick={() => history.push('/account')}
              >
                My Account
              </Button>
            </HStack>
          </VStack>

          {/* Help Section */}
          <Card bg="gray.900" borderColor="yellow.600" borderWidth="1px" w="full">
            <CardBody>
              <VStack spacing={3}>
                <Heading size="sm" color="yellow.400">
                  Need Help?
                </Heading>
                <Text fontSize="sm" color="gray.400" textAlign="center">
                  If you experienced an error or have questions about pricing, our support team
                  is ready to assist you.
                </Text>
                <Button
                  size="sm"
                  variant="outline"
                  colorScheme="yellow"
                  as="a"
                  href="mailto:support@aitutor.com"
                >
                  Contact Support
                </Button>
              </VStack>
            </CardBody>
          </Card>

          {/* Credit Packages Preview */}
          <Card bg="gray.900" borderColor="gray.700" borderWidth="1px" w="full">
            <CardBody>
              <VStack spacing={4} align="stretch">
                <Heading size="sm" color="gray.300">
                  Available Credit Packages
                </Heading>

                <HStack justify="space-between" p={3} bg="gray.800" borderRadius="md">
                  <VStack align="start" spacing={0}>
                    <Text fontWeight="bold" color="white">
                      Starter Package
                    </Text>
                    <Text fontSize="sm" color="gray.400">
                      100 Credits
                    </Text>
                  </VStack>
                  <Text fontSize="xl" fontWeight="bold" color="yellow.400">
                    $9.99
                  </Text>
                </HStack>

                <HStack
                  justify="space-between"
                  p={3}
                  bg="gray.800"
                  borderRadius="md"
                  borderWidth="2px"
                  borderColor="yellow.600"
                >
                  <VStack align="start" spacing={0}>
                    <HStack>
                      <Text fontWeight="bold" color="white">
                        Pro Package
                      </Text>
                      <Text fontSize="xs" color="yellow.400" fontWeight="bold">
                        POPULAR
                      </Text>
                    </HStack>
                    <Text fontSize="sm" color="gray.400">
                      500 Credits
                    </Text>
                  </VStack>
                  <Text fontSize="xl" fontWeight="bold" color="yellow.400">
                    $39.99
                  </Text>
                </HStack>

                <HStack justify="space-between" p={3} bg="gray.800" borderRadius="md">
                  <VStack align="start" spacing={0}>
                    <Text fontWeight="bold" color="white">
                      Unlimited Package
                    </Text>
                    <Text fontSize="sm" color="gray.400">
                      2000 Credits
                    </Text>
                  </VStack>
                  <Text fontSize="xl" fontWeight="bold" color="yellow.400">
                    $99.99
                  </Text>
                </HStack>

                <Text fontSize="xs" color="gray.500" textAlign="center">
                  All payments are secure and processed through Stripe
                </Text>
              </VStack>
            </CardBody>
          </Card>
        </VStack>
      </Container>
    </Box>
  );
}
