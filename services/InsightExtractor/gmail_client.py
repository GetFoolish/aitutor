"""
Gmail API Client - Production-ready implementation for fetching and parsing emails
"""
import os
import base64
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, AsyncGenerator
from dataclasses import dataclass
from email.utils import parsedate_to_datetime

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from shared.logging_config import get_logger

logger = get_logger(__name__)


# Learning platform domains to filter
LEARNING_PLATFORM_DOMAINS = [
    "coursera.org", "udemy.com", "edx.org", "khanacademy.org",
    "skillshare.com", "linkedin.com", "pluralsight.com",
    "codecademy.com", "brilliant.org", "masterclass.com",
    "udacity.com", "datacamp.com", "treehouse.com",
    "lynda.com", "futurelearn.com", "openlearning.com",
    "alison.com", "sololearn.com", "mimo.org",
    "duolingo.com", "babbel.com", "memrise.com"
]

# Newsletter platform domains
NEWSLETTER_DOMAINS = [
    "medium.com", "substack.com", "mailchimp.com",
    "convertkit.com", "beehiiv.com", "buttondown.email",
    "revue.co", "ghost.io", "tinyletter.com",
    "morningbrew.com", "themorningbrew.com",
    "tldr.tech", "hackernewsletter.com"
]

# Keywords indicating learning-related emails
LEARNING_KEYWORDS = [
    "course", "enroll", "certificate", "completed", "progress",
    "lesson", "module", "quiz", "assignment", "lecture",
    "learning path", "skill", "certification", "credential",
    "welcome to", "started learning", "continue learning"
]

# Receipt/purchase keywords
RECEIPT_KEYWORDS = [
    "receipt", "invoice", "payment", "purchase", "order",
    "subscription", "billing", "charged", "transaction"
]


@dataclass
class RawEmail:
    """Raw email data from Gmail API"""
    message_id: str
    thread_id: str
    sender: str
    sender_email: str
    sender_domain: str
    subject: str
    snippet: str
    body_text: str
    date: datetime
    labels: List[str]
    is_unread: bool


class GmailClient:
    """
    Production Gmail API client for extracting learning insights.

    Handles:
    - OAuth token management with refresh
    - Batch email fetching with pagination
    - Smart filtering for learning-related emails
    - Rate limiting compliance
    """

    def __init__(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_expiry: Optional[datetime] = None
    ):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expiry = token_expiry
        self._service = None
        self._credentials = None

    def _get_credentials(self) -> Credentials:
        """Build OAuth credentials from tokens"""
        if self._credentials and self._credentials.valid:
            return self._credentials

        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

        self._credentials = Credentials(
            token=self.access_token,
            refresh_token=self.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret
        )

        # Refresh if expired
        if self._credentials.expired and self._credentials.refresh_token:
            try:
                self._credentials.refresh(Request())
                self.access_token = self._credentials.token
                logger.info("[GMAIL] Refreshed access token")
            except Exception as e:
                logger.error(f"[GMAIL] Failed to refresh token: {e}")
                raise

        return self._credentials

    def _get_service(self):
        """Get or create Gmail API service"""
        if self._service is None:
            credentials = self._get_credentials()
            self._service = build('gmail', 'v1', credentials=credentials)
        return self._service

    def _extract_sender_info(self, headers: List[Dict]) -> tuple:
        """Extract sender name, email, and domain from headers"""
        sender = ""
        sender_email = ""
        sender_domain = ""

        for header in headers:
            if header['name'].lower() == 'from':
                sender = header['value']
                # Parse email from "Name <email@domain.com>" format
                if '<' in sender and '>' in sender:
                    sender_email = sender[sender.index('<')+1:sender.index('>')]
                else:
                    sender_email = sender

                if '@' in sender_email:
                    sender_domain = sender_email.split('@')[1].lower()
                break

        return sender, sender_email, sender_domain

    def _extract_date(self, headers: List[Dict]) -> datetime:
        """Extract and parse date from headers"""
        for header in headers:
            if header['name'].lower() == 'date':
                try:
                    return parsedate_to_datetime(header['value'])
                except Exception:
                    pass
        return datetime.now()

    def _extract_subject(self, headers: List[Dict]) -> str:
        """Extract subject from headers"""
        for header in headers:
            if header['name'].lower() == 'subject':
                return header['value']
        return ""

    def _decode_body(self, payload: Dict) -> str:
        """Decode email body from payload"""
        body_text = ""

        if 'body' in payload and 'data' in payload['body']:
            try:
                body_text = base64.urlsafe_b64decode(
                    payload['body']['data']
                ).decode('utf-8', errors='ignore')
            except Exception:
                pass

        # Handle multipart messages
        if 'parts' in payload:
            for part in payload['parts']:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/plain':
                    if 'body' in part and 'data' in part['body']:
                        try:
                            body_text = base64.urlsafe_b64decode(
                                part['body']['data']
                            ).decode('utf-8', errors='ignore')
                            break
                        except Exception:
                            pass
                elif mime_type.startswith('multipart/'):
                    # Recursive handling for nested multipart
                    nested_body = self._decode_body(part)
                    if nested_body:
                        body_text = nested_body
                        break

        return body_text[:5000]  # Limit body size

    def _build_search_query(self, lookback_days: int = 180) -> str:
        """
        Build Gmail search query to filter learning-related emails.
        Uses Gmail's search operators for efficient server-side filtering.
        """
        # Date filter
        after_date = datetime.now() - timedelta(days=lookback_days)
        date_filter = f"after:{after_date.strftime('%Y/%m/%d')}"

        # Domain filters for learning platforms
        domain_filters = " OR ".join([f"from:{domain}" for domain in LEARNING_PLATFORM_DOMAINS[:15]])

        # Newsletter domain filters
        newsletter_filters = " OR ".join([f"from:{domain}" for domain in NEWSLETTER_DOMAINS[:10]])

        # Keyword filters
        keyword_filters = " OR ".join(LEARNING_KEYWORDS[:10])

        # Combine: (learning platforms OR newsletters OR keywords) AND date
        query = f"({domain_filters} OR {newsletter_filters} OR ({keyword_filters})) {date_filter}"

        return query

    async def fetch_emails(
        self,
        max_emails: int = 500,
        lookback_days: int = 180,
        subject_only: bool = False
    ) -> List[RawEmail]:
        """
        Fetch learning-related emails from Gmail.

        Args:
            max_emails: Maximum number of emails to fetch
            lookback_days: How far back to search (in days)
            subject_only: If True, only fetch subject/metadata (faster, less tokens)

        Returns:
            List of RawEmail objects
        """
        service = self._get_service()
        emails = []

        query = self._build_search_query(lookback_days)
        logger.info(f"[GMAIL] Searching with query: {query[:100]}...")
        logger.info(f"[GMAIL] Mode: {'subject_only' if subject_only else 'full'}, lookback: {lookback_days} days")

        try:
            # List messages matching query
            page_token = None
            fetched_count = 0

            while fetched_count < max_emails:
                batch_size = min(100, max_emails - fetched_count)

                results = service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=batch_size,
                    pageToken=page_token
                ).execute()

                messages = results.get('messages', [])
                if not messages:
                    break

                logger.info(f"[GMAIL] Found {len(messages)} messages in batch")

                # Fetch message details
                for msg_info in messages:
                    try:
                        if subject_only:
                            # Metadata-only fetch (faster, no body)
                            msg = service.users().messages().get(
                                userId='me',
                                id=msg_info['id'],
                                format='metadata',
                                metadataHeaders=['From', 'Subject', 'Date']
                            ).execute()

                            headers = msg.get('payload', {}).get('headers', [])
                            sender, sender_email, sender_domain = self._extract_sender_info(headers)

                            raw_email = RawEmail(
                                message_id=msg['id'],
                                thread_id=msg.get('threadId', ''),
                                sender=sender,
                                sender_email=sender_email,
                                sender_domain=sender_domain,
                                subject=self._extract_subject(headers),
                                snippet=msg.get('snippet', ''),
                                body_text='',  # Not fetched in subject_only mode
                                date=self._extract_date(headers),
                                labels=msg.get('labelIds', []),
                                is_unread='UNREAD' in msg.get('labelIds', [])
                            )
                        else:
                            # Full fetch (includes body)
                            msg = service.users().messages().get(
                                userId='me',
                                id=msg_info['id'],
                                format='full'
                            ).execute()

                            payload = msg.get('payload', {})
                            headers = payload.get('headers', [])
                            sender, sender_email, sender_domain = self._extract_sender_info(headers)

                            raw_email = RawEmail(
                                message_id=msg['id'],
                                thread_id=msg.get('threadId', ''),
                                sender=sender,
                                sender_email=sender_email,
                                sender_domain=sender_domain,
                                subject=self._extract_subject(headers),
                                snippet=msg.get('snippet', ''),
                                body_text=self._decode_body(payload),
                                date=self._extract_date(headers),
                                labels=msg.get('labelIds', []),
                                is_unread='UNREAD' in msg.get('labelIds', [])
                            )

                        emails.append(raw_email)
                        fetched_count += 1

                    except HttpError as e:
                        logger.warning(f"[GMAIL] Error fetching message {msg_info['id']}: {e}")
                        continue

                # Check for next page
                page_token = results.get('nextPageToken')
                if not page_token:
                    break

                # Rate limiting - small delay between batches
                await asyncio.sleep(0.1)

            logger.info(f"[GMAIL] Successfully fetched {len(emails)} emails")
            return emails

        except HttpError as e:
            logger.error(f"[GMAIL] API error: {e}")
            raise

    def filter_by_domain(
        self,
        emails: List[RawEmail],
        domains: List[str]
    ) -> List[RawEmail]:
        """Filter emails by sender domain"""
        return [
            email for email in emails
            if any(domain in email.sender_domain for domain in domains)
        ]

    def filter_learning_platforms(self, emails: List[RawEmail]) -> List[RawEmail]:
        """Filter to only learning platform emails"""
        return self.filter_by_domain(emails, LEARNING_PLATFORM_DOMAINS)

    def filter_newsletters(self, emails: List[RawEmail]) -> List[RawEmail]:
        """Filter to only newsletter emails"""
        return self.filter_by_domain(emails, NEWSLETTER_DOMAINS)

    def group_by_sender(self, emails: List[RawEmail]) -> Dict[str, List[RawEmail]]:
        """Group emails by sender domain"""
        grouped = {}
        for email in emails:
            domain = email.sender_domain
            if domain not in grouped:
                grouped[domain] = []
            grouped[domain].append(email)
        return grouped

    async def get_calendar_events(
        self,
        lookback_months: int = 3
    ) -> List[Dict]:
        """
        Fetch calendar events that might indicate learning activities.
        Requires calendar.readonly scope.
        """
        try:
            credentials = self._get_credentials()
            calendar_service = build('calendar', 'v3', credentials=credentials)

            # Time range
            now = datetime.utcnow()
            time_min = (now - timedelta(days=lookback_months * 30)).isoformat() + 'Z'
            time_max = now.isoformat() + 'Z'

            # Search for learning-related events
            events_result = calendar_service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=100,
                singleEvents=True,
                orderBy='startTime',
                q='study OR course OR class OR lesson OR tutoring OR learning'
            ).execute()

            events = events_result.get('items', [])

            learning_events = []
            for event in events:
                learning_events.append({
                    'id': event.get('id'),
                    'summary': event.get('summary', ''),
                    'description': event.get('description', ''),
                    'start': event.get('start', {}).get('dateTime'),
                    'end': event.get('end', {}).get('dateTime'),
                    'recurring': event.get('recurringEventId') is not None
                })

            logger.info(f"[CALENDAR] Found {len(learning_events)} learning-related events")
            return learning_events

        except HttpError as e:
            logger.warning(f"[CALENDAR] API error (calendar access may not be granted): {e}")
            return []
        except Exception as e:
            logger.warning(f"[CALENDAR] Error fetching events: {e}")
            return []


class GmailOAuthHandler:
    """
    Handles Gmail-specific OAuth flow with extended scopes.
    """

    GMAIL_SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/calendar.readonly"
    ]

    def __init__(self, redirect_uri: str):
        self.redirect_uri = redirect_uri
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    def get_authorization_url(self, state: str) -> str:
        """
        Generate Gmail OAuth authorization URL with required scopes.

        Args:
            state: CSRF protection state parameter

        Returns:
            Authorization URL for Gmail consent
        """
        from urllib.parse import urlencode

        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(self.GMAIL_SCOPES),
            'access_type': 'offline',  # Get refresh token
            'prompt': 'consent',  # Force consent screen for refresh token
            'state': state
        }

        base_url = 'https://accounts.google.com/o/oauth2/v2/auth'
        return f"{base_url}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> Dict:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code from callback

        Returns:
            Dict with access_token, refresh_token, expires_in
        """
        import aiohttp

        token_url = 'https://oauth2.googleapis.com/token'

        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"[GMAIL_OAUTH] Token exchange failed: {error_text}")
                    raise Exception(f"Token exchange failed: {error_text}")

                tokens = await response.json()

                return {
                    'access_token': tokens.get('access_token'),
                    'refresh_token': tokens.get('refresh_token'),
                    'expires_in': tokens.get('expires_in', 3600),
                    'token_type': tokens.get('token_type', 'Bearer')
                }

    async def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        Refresh an expired access token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            Dict with new access_token and expires_in
        """
        import aiohttp

        token_url = 'https://oauth2.googleapis.com/token'

        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"[GMAIL_OAUTH] Token refresh failed: {error_text}")
                    raise Exception(f"Token refresh failed: {error_text}")

                tokens = await response.json()

                return {
                    'access_token': tokens.get('access_token'),
                    'expires_in': tokens.get('expires_in', 3600)
                }
