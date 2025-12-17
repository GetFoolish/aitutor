/**
 * Athena Math Input Module
 *
 * Provides math expression input components with keypad support.
 */

export { MathKeypad, FloatingMathKeypad, useMathKeypad } from './MathKeypad';
export type { MathKeypadProps } from './MathKeypad';

export { MathQuillWrapper, StaticMath } from './MathQuillWrapper';
export type { MathQuillWrapperProps, MathQuillWrapperRef } from './MathQuillWrapper';

export { ExpressionInput, ExpressionDisplay } from './ExpressionInput';
export type { ExpressionInputProps, ExpressionInputRef } from './ExpressionInput';

export {
  BASIC_SET,
  ALGEBRA_SET,
  TRIG_SET,
  CALCULUS_SET,
  CHEMISTRY_SET,
  getButtonSet,
  combineButtonSets,
  getAvailableButtonSets,
  createCustomButtonSet,
} from './ButtonSets';
export type { MathButton, ButtonSet, ButtonSetId } from './ButtonSets';
