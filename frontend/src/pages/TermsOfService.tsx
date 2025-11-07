import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  UnorderedList,
  ListItem,
  Link,
} from '@chakra-ui/react';
import { useHistory } from 'react-router-dom';

export function TermsOfService() {
  const history = useHistory();

  return (
    <Box minH="100vh" bg="black" color="white" py={12}>
      <Container maxW="4xl">
        <VStack spacing={8} align="stretch">
          <Box>
            <Link
              onClick={() => history.push('/')}
              color="yellow.400"
              fontSize="sm"
              _hover={{ textDecoration: 'underline' }}
              cursor="pointer"
            >
              ← Back to Home
            </Link>
          </Box>

          <Heading size="2xl" color="yellow.400">
            Terms of Service
          </Heading>

          <Text color="gray.400" fontSize="sm">
            Last Updated: {new Date().toLocaleDateString()}
          </Text>

          <VStack spacing={6} align="stretch">
            <Box>
              <Heading size="lg" mb={3}>
                1. Acceptance of Terms
              </Heading>
              <Text color="gray.300">
                By accessing and using AI Tutor, you accept and agree to be bound by the terms and
                provisions of this agreement. If you do not agree to these terms, please do not use
                our service.
              </Text>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                2. Description of Service
              </Heading>
              <Text color="gray.300" mb={3}>
                AI Tutor provides an interactive educational platform that uses artificial
                intelligence to deliver personalized learning experiences. Our services include:
              </Text>
              <UnorderedList color="gray.300" spacing={2} pl={4}>
                <ListItem>Adaptive question generation and assessment</ListItem>
                <ListItem>Voice-enabled AI tutoring sessions</ListItem>
                <ListItem>Video recommendations for educational content</ListItem>
                <ListItem>Progress tracking and skill mastery monitoring</ListItem>
                <ListItem>Parent dashboard for monitoring child accounts</ListItem>
              </UnorderedList>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                3. User Accounts
              </Heading>
              <Text color="gray.300" mb={3}>
                To use certain features of AI Tutor, you must create an account. You agree to:
              </Text>
              <UnorderedList color="gray.300" spacing={2} pl={4}>
                <ListItem>Provide accurate and complete registration information</ListItem>
                <ListItem>Maintain the security of your password</ListItem>
                <ListItem>
                  Notify us immediately of any unauthorized use of your account
                </ListItem>
                <ListItem>Accept responsibility for all activities under your account</ListItem>
              </UnorderedList>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                4. Credits and Payments
              </Heading>
              <Text color="gray.300" mb={3}>
                Our service operates on a credit-based system:
              </Text>
              <UnorderedList color="gray.300" spacing={2} pl={4}>
                <ListItem>Credits are required to access tutoring sessions</ListItem>
                <ListItem>Credits can be purchased through our payment system</ListItem>
                <ListItem>Credits are non-refundable once purchased</ListItem>
                <ListItem>Credits do not expire</ListItem>
                <ListItem>
                  Prices and credit packages may change with advance notice
                </ListItem>
              </UnorderedList>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                5. Parent and Child Accounts
              </Heading>
              <Text color="gray.300" mb={3}>
                For parent accounts:
              </Text>
              <UnorderedList color="gray.300" spacing={2} pl={4}>
                <ListItem>
                  Parents can create multiple child accounts under their supervision
                </ListItem>
                <ListItem>Parents are responsible for monitoring their children's usage</ListItem>
                <ListItem>Parents can view progress and learning analytics</ListItem>
                <ListItem>
                  Parents must ensure their children comply with these terms
                </ListItem>
              </UnorderedList>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                6. Privacy and Data Protection
              </Heading>
              <Text color="gray.300">
                Your privacy is important to us. Please review our{' '}
                <Link
                  color="yellow.400"
                  onClick={() => history.push('/privacy-policy')}
                  cursor="pointer"
                >
                  Privacy Policy
                </Link>{' '}
                to understand how we collect, use, and protect your information.
              </Text>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                7. Acceptable Use
              </Heading>
              <Text color="gray.300" mb={3}>
                You agree not to:
              </Text>
              <UnorderedList color="gray.300" spacing={2} pl={4}>
                <ListItem>Use the service for any unlawful purpose</ListItem>
                <ListItem>Attempt to gain unauthorized access to our systems</ListItem>
                <ListItem>Share your account credentials with others</ListItem>
                <ListItem>
                  Interfere with or disrupt the service or servers
                </ListItem>
                <ListItem>Use automated systems to access the service</ListItem>
              </UnorderedList>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                8. Intellectual Property
              </Heading>
              <Text color="gray.300">
                All content, features, and functionality of AI Tutor are owned by us and are
                protected by copyright, trademark, and other intellectual property laws. You may
                not reproduce, distribute, or create derivative works without our express written
                permission.
              </Text>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                9. Disclaimers and Limitation of Liability
              </Heading>
              <Text color="gray.300" mb={3}>
                AI Tutor is provided "as is" without warranties of any kind. We do not guarantee:
              </Text>
              <UnorderedList color="gray.300" spacing={2} pl={4}>
                <ListItem>Uninterrupted or error-free service</ListItem>
                <ListItem>Specific learning outcomes or results</ListItem>
                <ListItem>Accuracy or completeness of educational content</ListItem>
                <ListItem>Compatibility with all devices or browsers</ListItem>
              </UnorderedList>
              <Text color="gray.300" mt={3}>
                We shall not be liable for any indirect, incidental, special, or consequential
                damages arising from your use of the service.
              </Text>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                10. Termination
              </Heading>
              <Text color="gray.300">
                We reserve the right to suspend or terminate your account at any time for
                violations of these terms. Upon termination, your right to use the service will
                immediately cease, and unused credits will be forfeited.
              </Text>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                11. Changes to Terms
              </Heading>
              <Text color="gray.300">
                We may update these terms from time to time. We will notify you of significant
                changes by email or through the service. Your continued use after such changes
                constitutes acceptance of the new terms.
              </Text>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                12. Contact Information
              </Heading>
              <Text color="gray.300">
                If you have questions about these Terms of Service, please contact us at:
              </Text>
              <Text color="yellow.400" mt={2}>
                support@aitutor.com
              </Text>
            </Box>
          </VStack>

          <Box borderTopWidth="1px" borderColor="gray.700" pt={6}>
            <Text color="gray.500" fontSize="sm" textAlign="center">
              © {new Date().getFullYear()} AI Tutor. All rights reserved.
            </Text>
          </Box>
        </VStack>
      </Container>
    </Box>
  );
}
