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

export function PrivacyPolicy() {
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
            Privacy Policy
          </Heading>

          <Text color="gray.400" fontSize="sm">
            Last Updated: {new Date().toLocaleDateString()}
          </Text>

          <VStack spacing={6} align="stretch">
            <Box>
              <Heading size="lg" mb={3}>
                1. Introduction
              </Heading>
              <Text color="gray.300">
                At AI Tutor, we take your privacy seriously. This Privacy Policy explains how we
                collect, use, disclose, and safeguard your information when you use our
                educational platform. Please read this policy carefully to understand our practices
                regarding your personal data.
              </Text>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                2. Information We Collect
              </Heading>
              <Text color="gray.300" mb={3}>
                We collect several types of information to provide and improve our service:
              </Text>

              <Heading size="md" mb={2} color="yellow.300">
                Personal Information
              </Heading>
              <UnorderedList color="gray.300" spacing={2} pl={4} mb={4}>
                <ListItem>Name and email address</ListItem>
                <ListItem>Age (for child accounts)</ListItem>
                <ListItem>Language and region preferences</ListItem>
                <ListItem>Profile picture (if provided via OAuth)</ListItem>
                <ListItem>Parent-child account relationships</ListItem>
              </UnorderedList>

              <Heading size="md" mb={2} color="yellow.300">
                Learning Data
              </Heading>
              <UnorderedList color="gray.300" spacing={2} pl={4} mb={4}>
                <ListItem>Questions answered and quiz attempts</ListItem>
                <ListItem>Skill mastery levels and progress</ListItem>
                <ListItem>Response times and accuracy rates</ListItem>
                <ListItem>Learning path and skill prerequisites</ListItem>
              </UnorderedList>

              <Heading size="md" mb={2} color="yellow.300">
                Usage Information
              </Heading>
              <UnorderedList color="gray.300" spacing={2} pl={4} mb={4}>
                <ListItem>Session duration and frequency</ListItem>
                <ListItem>Feature usage patterns</ListItem>
                <ListItem>Device and browser information</ListItem>
                <ListItem>IP address and general location</ListItem>
              </UnorderedList>

              <Heading size="md" mb={2} color="yellow.300">
                Communication Data
              </Heading>
              <UnorderedList color="gray.300" spacing={2} pl={4}>
                <ListItem>Voice recordings during tutoring sessions</ListItem>
                <ListItem>Text transcripts of conversations</ListItem>
                <ListItem>Video recordings (if camera is enabled)</ListItem>
                <ListItem>Screen sharing content (if enabled)</ListItem>
              </UnorderedList>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                3. How We Use Your Information
              </Heading>
              <Text color="gray.300" mb={3}>
                We use the collected information for the following purposes:
              </Text>
              <UnorderedList color="gray.300" spacing={2} pl={4}>
                <ListItem>Providing personalized educational experiences</ListItem>
                <ListItem>Adapting difficulty levels based on performance</ListItem>
                <ListItem>Generating relevant questions and content</ListItem>
                <ListItem>Tracking learning progress and skill mastery</ListItem>
                <ListItem>Recommending educational videos and resources</ListItem>
                <ListItem>Processing payments and managing credits</ListItem>
                <ListItem>Enabling parent monitoring of child accounts</ListItem>
                <ListItem>Improving our AI models and algorithms</ListItem>
                <ListItem>Communicating service updates and notifications</ListItem>
                <ListItem>Ensuring platform security and preventing fraud</ListItem>
              </UnorderedList>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                4. Data Storage and Security
              </Heading>
              <Text color="gray.300" mb={3}>
                We implement industry-standard security measures to protect your data:
              </Text>
              <UnorderedList color="gray.300" spacing={2} pl={4}>
                <ListItem>Encrypted data transmission using HTTPS/TLS</ListItem>
                <ListItem>Password hashing with bcrypt</ListItem>
                <ListItem>Secure JWT token-based authentication</ListItem>
                <ListItem>MongoDB database with access controls</ListItem>
                <ListItem>Regular security audits and updates</ListItem>
                <ListItem>Limited employee access to personal data</ListItem>
              </UnorderedList>
              <Text color="gray.300" mt={3}>
                While we strive to protect your information, no method of transmission over the
                Internet is 100% secure. We cannot guarantee absolute security.
              </Text>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                5. Data Sharing and Disclosure
              </Heading>
              <Text color="gray.300" mb={3}>
                We do not sell your personal information. We may share data in the following
                circumstances:
              </Text>
              <UnorderedList color="gray.300" spacing={2} pl={4}>
                <ListItem>
                  <strong>Service Providers:</strong> Third-party services that help us operate
                  (payment processing, cloud hosting, analytics)
                </ListItem>
                <ListItem>
                  <strong>AI Providers:</strong> Google Gemini, Anthropic Claude for AI
                  processing (subject to their privacy policies)
                </ListItem>
                <ListItem>
                  <strong>Parent Accounts:</strong> Parents can view their children's learning
                  progress and activity
                </ListItem>
                <ListItem>
                  <strong>Legal Requirements:</strong> When required by law, court order, or
                  government request
                </ListItem>
                <ListItem>
                  <strong>Business Transfers:</strong> In connection with a merger, acquisition, or
                  sale of assets
                </ListItem>
              </UnorderedList>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                6. Children's Privacy (COPPA Compliance)
              </Heading>
              <Text color="gray.300" mb={3}>
                We are committed to protecting children's privacy:
              </Text>
              <UnorderedList color="gray.300" spacing={2} pl={4}>
                <ListItem>
                  Child accounts must be created by a verified parent
                </ListItem>
                <ListItem>Parents control their children's accounts and data</ListItem>
                <ListItem>
                  We collect only necessary information for educational purposes
                </ListItem>
                <ListItem>Parents can review, update, or delete child data at any time</ListItem>
                <ListItem>We do not knowingly allow children under 13 to create independent accounts</ListItem>
              </UnorderedList>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                7. Your Rights and Choices
              </Heading>
              <Text color="gray.300" mb={3}>
                You have the following rights regarding your personal data:
              </Text>
              <UnorderedList color="gray.300" spacing={2} pl={4}>
                <ListItem>
                  <strong>Access:</strong> Request a copy of your personal data
                </ListItem>
                <ListItem>
                  <strong>Correction:</strong> Update inaccurate or incomplete information
                </ListItem>
                <ListItem>
                  <strong>Deletion:</strong> Request deletion of your account and data
                </ListItem>
                <ListItem>
                  <strong>Export:</strong> Download your learning data in a portable format
                </ListItem>
                <ListItem>
                  <strong>Opt-Out:</strong> Unsubscribe from marketing communications
                </ListItem>
                <ListItem>
                  <strong>Restrict Processing:</strong> Limit how we use certain data
                </ListItem>
              </UnorderedList>
              <Text color="gray.300" mt={3}>
                To exercise these rights, please contact us at{' '}
                <Link color="yellow.400" href="mailto:privacy@aitutor.com">
                  privacy@aitutor.com
                </Link>
              </Text>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                8. Cookies and Tracking Technologies
              </Heading>
              <Text color="gray.300">
                We use cookies and similar technologies to enhance your experience, maintain
                session state, and analyze usage patterns. You can control cookie preferences
                through your browser settings, though this may affect certain features.
              </Text>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                9. Third-Party Services
              </Heading>
              <Text color="gray.300" mb={3}>
                Our platform integrates with third-party services:
              </Text>
              <UnorderedList color="gray.300" spacing={2} pl={4}>
                <ListItem>Google OAuth for authentication</ListItem>
                <ListItem>Stripe for payment processing</ListItem>
                <ListItem>YouTube API for video recommendations</ListItem>
                <ListItem>Google Gemini and Anthropic Claude for AI services</ListItem>
                <ListItem>Pipecat AI for voice interactions</ListItem>
              </UnorderedList>
              <Text color="gray.300" mt={3}>
                These services have their own privacy policies, and we encourage you to review them.
              </Text>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                10. International Data Transfers
              </Heading>
              <Text color="gray.300">
                Your data may be transferred to and processed in countries other than your own. We
                ensure appropriate safeguards are in place to protect your information in
                accordance with this Privacy Policy.
              </Text>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                11. Data Retention
              </Heading>
              <Text color="gray.300">
                We retain your personal data for as long as your account is active or as needed to
                provide services. Learning data is retained to track progress and improve
                personalization. You can request deletion of your data at any time.
              </Text>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                12. Changes to This Policy
              </Heading>
              <Text color="gray.300">
                We may update this Privacy Policy periodically. We will notify you of significant
                changes by email or through a prominent notice on our platform. The "Last Updated"
                date at the top indicates when changes were made.
              </Text>
            </Box>

            <Box>
              <Heading size="lg" mb={3}>
                13. Contact Us
              </Heading>
              <Text color="gray.300">
                If you have questions or concerns about this Privacy Policy, please contact us:
              </Text>
              <VStack align="start" mt={3} color="yellow.400">
                <Text>Email: privacy@aitutor.com</Text>
                <Text>Support: support@aitutor.com</Text>
              </VStack>
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
