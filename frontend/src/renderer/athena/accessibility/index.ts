/**
 * Athena Accessibility Module
 *
 * WCAG 2.1 AA compliant accessibility utilities.
 */

export {
  getWidgetAriaLabel,
  getWidgetStateDescription,
  getHintButtonAriaLabel,
  getScoreAriaLabel,
  getStateChangeAnnouncement,
  formatNumberForScreenReader,
  formatMathForScreenReader,
  getKeyboardShortcutDescription,
} from './AriaLabels';

export {
  useKeyboardNavigation,
  FocusTrap,
  SkipLink,
  useRovingTabIndex,
} from './KeyboardNavigation';
export type { KeyboardNavigationOptions, FocusTrapProps } from './KeyboardNavigation';

export {
  ScreenReaderAnnouncerProvider,
  useScreenReaderAnnouncer,
  ScreenReaderAnnouncer,
  VisuallyHidden,
  useAnnounceOnChange,
} from './ScreenReaderAnnouncer';
export type { Announcement, AnnouncementPoliteness, ScreenReaderAnnouncerContextValue } from './ScreenReaderAnnouncer';
