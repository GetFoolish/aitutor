import { useState, useEffect } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  VStack,
  HStack,
  Box,
  Text,
  Button,
  Badge,
  Icon,
  useToast,
  Spinner,
} from '@chakra-ui/react';
import { FaCoins, FaStar, FaCrown, FaRocket } from 'react-icons/fa';
import { useAuth } from '../../contexts/AuthContext';

interface CreditPackage {
  id: string;
  name: string;
  credits: number;
  price_usd: number;
  icon?: any;
  popular?: boolean;
}

interface CreditsPurchaseModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CreditsPurchaseModal({ isOpen, onClose }: CreditsPurchaseModalProps) {
  const { token } = useAuth();
  const toast = useToast();
  const [packages, setPackages] = useState<CreditPackage[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchPackages();
    }
  }, [isOpen]);

  const fetchPackages = async () => {
    try {
      const response = await fetch('http://localhost:8001/payments/packages');
      const data = await response.json();

      setPackages(data.packages.map((pkg: CreditPackage) => ({
        ...pkg,
        icon: pkg.id === 'starter' ? FaStar : pkg.id === 'pro' ? FaCrown : FaRocket,
        popular: pkg.id === 'pro',
      })));
    } catch (error) {
      console.error('Failed to fetch packages:', error);
    }
  };

  const handlePurchase = async (packageId: string) => {
    if (!token) {
      toast({
        title: 'Authentication required',
        description: 'Please log in to purchase credits',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    setLoading(true);

    try {
      const response = await fetch('http://localhost:8001/payments/create-checkout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          package_id: packageId,
          success_url: `${window.location.origin}/payment/success`,
          cancel_url: `${window.location.origin}/payment/cancel`,
        }),
      });

      if (response.ok) {
        const { checkout_url } = await response.json();
        // Redirect to Stripe Checkout
        window.location.href = checkout_url;
      } else {
        const error = await response.json();
        throw new Error(error.detail);
      }
    } catch (error: any) {
      toast({
        title: 'Purchase failed',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl" isCentered closeOnOverlayClick={true}>
      <ModalOverlay bg="blackAlpha.800" backdropFilter="blur(4px)" />
      <ModalContent bg="black" color="white" borderRadius="xl" borderWidth="1px" borderColor="gray.700">
        <ModalHeader textAlign="center">
          <VStack spacing={2}>
            <Icon as={FaCoins} boxSize={12} color="purple.400" />
            <Text fontSize="2xl" fontWeight="bold">
              Purchase Credits
            </Text>
            <Text fontSize="sm" color="gray.400" fontWeight="normal">
              Power your learning journey
            </Text>
          </VStack>
        </ModalHeader>
        <ModalCloseButton color="white" _hover={{ bg: 'gray.800' }} />

        <ModalBody pb={6}>
          <VStack spacing={4}>
            {/* What Are Credits Explanation */}
            <Box
              w="full"
              p={4}
              borderRadius="md"
              bg="purple.900"
              borderWidth="1px"
              borderColor="purple.600"
            >
              <VStack spacing={2} align="start">
                <HStack>
                  <Icon as={FaCoins} color="purple.300" boxSize={5} />
                  <Text fontWeight="bold" color="purple.200">What are credits?</Text>
                </HStack>
                <Text fontSize="sm" color="purple.100">
                  Credits power your AI tutoring experience. Each credit unlocks:
                </Text>
                <VStack align="start" pl={4} spacing={1}>
                  <Text fontSize="sm" color="purple.100">• 1 question with AI explanation</Text>
                  <Text fontSize="sm" color="purple.100">• Voice conversation with tutor</Text>
                  <Text fontSize="sm" color="purple.100">• Video recommendations</Text>
                  <Text fontSize="sm" color="purple.100">• Progress tracking & insights</Text>
                </VStack>
                <Text fontSize="xs" color="purple.200" fontStyle="italic" mt={1}>
                  Credits never expire and work across all subjects!
                </Text>
              </VStack>
            </Box>

            {packages.map((pkg) => (
              <Box
                key={pkg.id}
                w="full"
                p={6}
                borderRadius="lg"
                borderWidth="2px"
                borderColor={pkg.popular ? 'purple.400' : 'gray.700'}
                bg={pkg.popular ? 'gray.900' : 'gray.800'}
                position="relative"
                _hover={{
                  borderColor: 'purple.400',
                  transform: 'scale(1.02)',
                }}
                transition="all 0.2s"
              >
                {pkg.popular && (
                  <Badge
                    position="absolute"
                    top="-3"
                    right="4"
                    colorScheme="purple"
                    fontSize="xs"
                    px={3}
                    py={1}
                  >
                    MOST POPULAR
                  </Badge>
                )}

                <HStack justify="space-between" align="start">
                  <HStack spacing={4}>
                    <Icon as={pkg.icon} boxSize={8} color="purple.400" />
                    <VStack align="start" spacing={1}>
                      <Text fontSize="xl" fontWeight="bold">
                        {pkg.name}
                      </Text>
                      <HStack>
                        <Icon as={FaCoins} color="purple.400" boxSize={4} />
                        <Text fontSize="lg" fontWeight="bold" color="purple.400">
                          {pkg.credits} Credits
                        </Text>
                      </HStack>
                      <Text fontSize="sm" color="gray.300" fontWeight="semibold">
                        ≈ {pkg.credits} questions with full AI support
                      </Text>
                      <Text fontSize="xs" color="gray.500">
                        ${(pkg.price_usd / pkg.credits).toFixed(3)} per credit
                      </Text>
                    </VStack>
                  </HStack>

                  <VStack align="end" spacing={2}>
                    <Text fontSize="3xl" fontWeight="bold">
                      ${pkg.price_usd}
                    </Text>
                    <Button
                      colorScheme="purple"
                      size="lg"
                      onClick={() => handlePurchase(pkg.id)}
                      isLoading={loading}
                      bg="purple.500"
                      color="white"
                      _hover={{ bg: 'purple.600' }}
                    >
                      Buy Now
                    </Button>
                  </VStack>
                </HStack>
              </Box>
            ))}

            <Box
              w="full"
              p={6}
              borderRadius="lg"
              borderWidth="2px"
              borderColor="purple.500"
              bg="gray.800"
              textAlign="center"
            >
              <VStack spacing={3}>
                <Icon as={FaCrown} boxSize={10} color="purple.400" />
                <Text fontSize="xl" fontWeight="bold">
                  Want Unlimited Access?
                </Text>
                <Text fontSize="sm" color="gray.400">
                  Get unlimited credits with our monthly subscription
                </Text>
                <Text fontSize="2xl" fontWeight="bold">
                  $29.99/month
                </Text>
                <Button
                  colorScheme="purple"
                  size="lg"
                  onClick={() => {
                    toast({
                      title: 'Coming Soon!',
                      description: 'Subscription plans will be available soon',
                      status: 'info',
                      duration: 3000,
                    });
                  }}
                >
                  Subscribe
                </Button>
              </VStack>
            </Box>

            {/* Trust & Security */}
            <VStack spacing={2} pt={2}>
              <HStack spacing={6} color="gray.400" fontSize="xs">
                <HStack>
                  <Text>🔒</Text>
                  <Text>Secure Payment</Text>
                </HStack>
                <HStack>
                  <Text>♾️</Text>
                  <Text>Never Expire</Text>
                </HStack>
                <HStack>
                  <Text>🔄</Text>
                  <Text>30-Day Refund</Text>
                </HStack>
              </HStack>
              <Text fontSize="xs" color="gray.500" textAlign="center">
                Powered by Stripe • Click outside to close
              </Text>
            </VStack>
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}
