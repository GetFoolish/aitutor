import { describe, it, expect } from 'vitest';
import { deepNormalize, scorePerseusQuestion, hasUserInput } from './scoring-utils';

// ============================================================================
// deepNormalize()
// ============================================================================

describe('deepNormalize', () => {
  describe('whitespace stripping', () => {
    it('removes all spaces', () => {
      // '2+3' → terms ['+2','+3'] → sorted → '2+3'
      expect(deepNormalize('  2 + 3  ')).toBe('2+3');
    });
    it('removes tabs and newlines', () => {
      expect(deepNormalize('\t2\n+\t3')).toBe('2+3');
    });
    it('lowercases letters', () => {
      // 'x+y' → terms ['+x','+y'] → sorted → 'x+y'
      expect(deepNormalize('X + Y')).toBe('x+y');
    });
    it('removes spaces in expressions without additive sort trigger', () => {
      // Use subtraction to avoid additive sorting, proving whitespace stripping works
      expect(deepNormalize('  2 - 3  ')).toBe('2-3');
    });
    it('lowercases without sorting when subtraction present', () => {
      expect(deepNormalize('X - Y')).toBe('x-y');
    });
  });

  describe('LaTeX wrapper removal', () => {
    it('strips \\text{}', () => {
      expect(deepNormalize('\\text{hello}')).toBe('hello');
    });
    it('strips \\mathrm{}', () => {
      expect(deepNormalize('\\mathrm{kg}')).toBe('kg');
    });
    it('strips \\mathit{}', () => {
      expect(deepNormalize('\\mathit{v}')).toBe('v');
    });
    it('handles nested content in \\text{}', () => {
      // After stripping \text{}, '2x+1' triggers additive sort → terms ['+2x','+1'] → sorted → '1+2x'
      expect(deepNormalize('\\text{2x+1}')).toBe('1+2x');
    });
    it('handles simple content in \\text{} without sort trigger', () => {
      // Single term — no sorting triggered
      expect(deepNormalize('\\text{hello}')).toBe('hello');
    });
  });

  describe('fraction conversion', () => {
    it('converts \\frac{a}{b} to (a)/(b) and simplifies', () => {
      // \frac{1}{2} → (1)/(2) → after trivial parens removal: 1/2
      expect(deepNormalize('\\frac{1}{2}')).toBe('1/2');
    });
    it('converts \\frac with multi-char numerator/denominator', () => {
      // \frac{12}{5} → (12)/(5) → 12/5
      expect(deepNormalize('\\frac{12}{5}')).toBe('12/5');
    });
    it('evaluates integer fractions completely', () => {
      // \frac{6}{3} → (6)/(3) → 6/3 → 2
      expect(deepNormalize('\\frac{6}{3}')).toBe('2');
    });
  });

  describe('multiplication symbol normalization', () => {
    it('normalizes Unicode multiplication sign (times)', () => {
      expect(deepNormalize('2\u00D73')).toBe('2*3');
    });
    it('normalizes Unicode middle dot (cdot)', () => {
      expect(deepNormalize('2\u00B73')).toBe('2*3');
    });
    it('normalizes \\cdot', () => {
      expect(deepNormalize('2\\cdot3')).toBe('2*3');
    });
    it('normalizes \\times', () => {
      expect(deepNormalize('2\\times3')).toBe('2*3');
    });
  });

  describe('brace removal', () => {
    it('removes simple braces', () => {
      expect(deepNormalize('{x}')).toBe('x');
    });
    it('removes nested braces', () => {
      expect(deepNormalize('{{x}}')).toBe('x');
    });
    it('removes multiple brace groups', () => {
      // After brace removal, 'a+b' triggers additive sort → terms ['+a','+b'] → sorted → 'a+b'
      expect(deepNormalize('{a}+{b}')).toBe('a+b');
    });
    it('removes braces without sort (single term)', () => {
      expect(deepNormalize('{abc}')).toBe('abc');
    });
  });

  describe('trivial parentheses removal', () => {
    it('removes parentheses around single token', () => {
      expect(deepNormalize('(2)')).toBe('2');
    });
    it('removes nested trivial parentheses', () => {
      expect(deepNormalize('((x))')).toBe('x');
    });
    it('does not remove non-trivial parentheses', () => {
      expect(deepNormalize('(2+3)')).toBe('(2+3)');
    });
  });

  describe('integer exponents', () => {
    it('evaluates 2^3 to 8', () => {
      expect(deepNormalize('2^3')).toBe('8');
    });
    it('evaluates 10^2 to 100', () => {
      expect(deepNormalize('10^2')).toBe('100');
    });
    it('does not evaluate if result >= 1e6 (uses strict < 1e6)', () => {
      // 10^6 = 1000000 which is NOT < 1e6, so it stays as-is
      expect(deepNormalize('10^6')).toBe('10^6');
      expect(deepNormalize('10^7')).toBe('10^7');
    });
    it('evaluates result just below 1e6', () => {
      // 999^2 = 998001 < 1e6 → evaluates
      expect(deepNormalize('999^2')).toBe('998001');
    });
    it('evaluates 5^0 to 1', () => {
      expect(deepNormalize('5^0')).toBe('1');
    });
  });

  describe('integer division', () => {
    it('evaluates 6/3 to 2', () => {
      expect(deepNormalize('6/3')).toBe('2');
    });
    it('evaluates 100/10 to 10', () => {
      expect(deepNormalize('100/10')).toBe('10');
    });
    it('does NOT evaluate non-integer division', () => {
      expect(deepNormalize('7/3')).toBe('7/3');
    });
    it('does NOT evaluate division by zero', () => {
      expect(deepNormalize('5/0')).toBe('5/0');
    });
    it('only applies when entire expression is a division', () => {
      // "6/3+1" should not simplify the 6/3 part
      expect(deepNormalize('6/3+1')).not.toBe('2+1');
    });
  });

  describe('additive commutativity', () => {
    it('commutative: 7+x equals x+7', () => {
      const a = deepNormalize('7+x');
      const b = deepNormalize('x+7');
      expect(a).toBe('7+x');
      expect(b).toBe('7+x');
      expect(a).toBe(b);
    });

    it('commutative: c+a+b equals a+b+c', () => {
      const a = deepNormalize('c+a+b');
      const b = deepNormalize('a+b+c');
      expect(a).toBe(b);
      expect(a).toBe('a+b+c');
    });

    it('commutative: different first terms still match', () => {
      const a = deepNormalize('a+c+b');
      const b = deepNormalize('a+b+c');
      expect(a).toBe(b);
    });
  });

  describe('subtraction NOT sorted', () => {
    it('does NOT sort when subtraction is present', () => {
      const a = deepNormalize('5-3');
      const b = deepNormalize('3-5');
      // These must remain different
      expect(a).not.toBe(b);
    });
  });

  describe('multiplication terms NOT sorted', () => {
    it('does not sort terms containing multiplication', () => {
      // 2*x+3 should not rearrange because * is present in terms
      const a = deepNormalize('2*x+3');
      const b = deepNormalize('3+2*x');
      // With multiplication present, sorting is disabled so order matters
      // Actually: terms are ["2*x", "+3"] — hasMultiplication is true, so no sorting
      expect(a).not.toBe(b);
    });
  });

  describe('empty/whitespace-only input', () => {
    it('returns empty string for empty input', () => {
      expect(deepNormalize('')).toBe('');
    });
    it('returns empty string for whitespace-only', () => {
      expect(deepNormalize('   ')).toBe('');
    });
    it('returns empty string for tabs', () => {
      expect(deepNormalize('\t\n')).toBe('');
    });
  });
});

// ============================================================================
// scorePerseusQuestion()
// ============================================================================

describe('scorePerseusQuestion', () => {

  // ---------- radio single ----------
  describe('radio single', () => {
    const widgets = {
      'radio 1': {
        type: 'radio',
        options: {
          choices: [
            { content: 'Wrong', correct: false },
            { content: 'Right', correct: true },
            { content: 'Also Wrong', correct: false },
          ],
          multipleSelect: false,
        },
      },
    };

    it('scores correct choice', () => {
      const result = scorePerseusQuestion(widgets, {
        'radio 1': { selectedChoiceIds: ['choice-1'] },
      });
      expect(result.correct).toBe(true);
      expect(result.scoreableCount).toBe(1);
      expect(result.correctCount).toBe(1);
      expect(result.selectedAnswerText).toBe('Right');
      expect(result.selectedAnswerIndex).toBe(1);
    });

    it('scores wrong choice', () => {
      const result = scorePerseusQuestion(widgets, {
        'radio 1': { selectedChoiceIds: ['choice-0'] },
      });
      expect(result.correct).toBe(false);
      expect(result.correctCount).toBe(0);
      expect(result.selectedAnswerText).toBe('Wrong');
      expect(result.selectedAnswerIndex).toBe(0);
    });

    it('scores empty selection as incorrect', () => {
      const result = scorePerseusQuestion(widgets, {
        'radio 1': { selectedChoiceIds: [] },
      });
      expect(result.correct).toBe(false);
      expect(result.correctCount).toBe(0);
    });

    it('scores correct choice when selectedChoiceIds uses explicit widget IDs', () => {
      const withIds = {
        'radio 1': {
          type: 'radio',
          options: {
            choices: [
              { id: '0-0-0-0-0', content: '"10"', correct: false },
              { id: '1-1-1-1-1', content: '"4"', correct: true },
            ],
            multipleSelect: false,
          },
        },
      };
      const result = scorePerseusQuestion(withIds, {
        'radio 1': { selectedChoiceIds: ['1-1-1-1-1'] },
      });
      expect(result.correct).toBe(true);
      expect(result.selectedAnswerText).toBe('4');
      expect(result.selectedAnswerIndex).toBe(1);
    });

    it('accepts quoted selectedChoiceId tokens', () => {
      const result = scorePerseusQuestion(widgets, {
        'radio 1': { selectedChoiceIds: ['"choice-1"'] },
      });
      expect(result.correct).toBe(true);
      expect(result.selectedAnswerIndex).toBe(1);
    });
  });

  // ---------- radio multi-select ----------
  describe('radio multi-select', () => {
    const widgets = {
      'radio 1': {
        type: 'radio',
        options: {
          choices: [
            { content: 'A', correct: true },
            { content: 'B', correct: false },
            { content: 'C', correct: true },
            { content: 'D', correct: false },
          ],
          multipleSelect: true,
        },
      },
    };

    it('all correct selected', () => {
      const result = scorePerseusQuestion(widgets, {
        'radio 1': { selectedChoiceIds: ['choice-0', 'choice-2'] },
      });
      expect(result.correct).toBe(true);
    });

    it('missing one correct choice', () => {
      const result = scorePerseusQuestion(widgets, {
        'radio 1': { selectedChoiceIds: ['choice-0'] },
      });
      expect(result.correct).toBe(false);
    });

    it('extra incorrect choice selected', () => {
      const result = scorePerseusQuestion(widgets, {
        'radio 1': { selectedChoiceIds: ['choice-0', 'choice-1', 'choice-2'] },
      });
      expect(result.correct).toBe(false);
    });

    it('completely wrong selection', () => {
      const result = scorePerseusQuestion(widgets, {
        'radio 1': { selectedChoiceIds: ['choice-1', 'choice-3'] },
      });
      expect(result.correct).toBe(false);
    });

    it('multi-select supports explicit choice IDs', () => {
      const withIds = {
        'radio 1': {
          type: 'radio',
          options: {
            choices: [
              { id: 'a-id', content: 'A', correct: true },
              { id: 'b-id', content: 'B', correct: false },
              { id: 'c-id', content: 'C', correct: true },
            ],
            multipleSelect: true,
          },
        },
      };
      const result = scorePerseusQuestion(withIds, {
        'radio 1': { selectedChoiceIds: ['a-id', 'c-id'] },
      });
      expect(result.correct).toBe(true);
    });
  });

  // ---------- numeric-input ----------
  describe('numeric-input', () => {
    const mkWidget = (value: number, maxError?: number) => ({
      'numeric-input 1': {
        type: 'numeric-input',
        options: {
          answers: [
            { status: 'correct', value, maxError: maxError ?? null },
          ],
        },
      },
    });

    it('exact match', () => {
      const result = scorePerseusQuestion(mkWidget(42, 0.5), {
        'numeric-input 1': { currentValue: '42' },
      });
      expect(result.correct).toBe(true);
      expect(result.selectedAnswerText).toBe('42');
    });

    it('within maxError', () => {
      const result = scorePerseusQuestion(mkWidget(42, 0.5), {
        'numeric-input 1': { currentValue: '42.3' },
      });
      expect(result.correct).toBe(true);
    });

    it('outside maxError', () => {
      const result = scorePerseusQuestion(mkWidget(42, 0.5), {
        'numeric-input 1': { currentValue: '43' },
      });
      expect(result.correct).toBe(false);
    });

    it('default maxError (1% of value) for non-zero', () => {
      // value=100, maxError defaults to max(0.01, 100*0.01)=1.0
      const result = scorePerseusQuestion(mkWidget(100), {
        'numeric-input 1': { currentValue: '100.9' },
      });
      expect(result.correct).toBe(true);
    });

    it('default maxError rejects values beyond 1%', () => {
      // value=100, maxError=1.0, so 101.5 is outside
      const result = scorePerseusQuestion(mkWidget(100), {
        'numeric-input 1': { currentValue: '101.5' },
      });
      expect(result.correct).toBe(false);
    });

    it('zero answer uses 0.001 maxError', () => {
      const result = scorePerseusQuestion(mkWidget(0), {
        'numeric-input 1': { currentValue: '0.0005' },
      });
      expect(result.correct).toBe(true);
    });

    it('zero answer rejects larger deviation', () => {
      const result = scorePerseusQuestion(mkWidget(0), {
        'numeric-input 1': { currentValue: '0.002' },
      });
      expect(result.correct).toBe(false);
    });

    it('NaN input is incorrect', () => {
      const result = scorePerseusQuestion(mkWidget(42, 0.5), {
        'numeric-input 1': { currentValue: 'abc' },
      });
      expect(result.correct).toBe(false);
    });

    it('empty input is incorrect', () => {
      const result = scorePerseusQuestion(mkWidget(42, 0.5), {
        'numeric-input 1': { currentValue: '' },
      });
      expect(result.correct).toBe(false);
    });
  });

  // ---------- dropdown ----------
  describe('dropdown', () => {
    const widgets = {
      'dropdown 1': {
        type: 'dropdown',
        options: {
          choices: [
            { content: 'First', correct: false },
            { content: 'Second', correct: true },
            { content: 'Third', correct: false },
          ],
        },
      },
    };

    it('correct index', () => {
      const result = scorePerseusQuestion(widgets, {
        'dropdown 1': { value: 1 },
      });
      expect(result.correct).toBe(true);
      expect(result.selectedAnswerText).toBe('Second');
      expect(result.selectedAnswerIndex).toBe(1);
    });

    it('wrong index', () => {
      const result = scorePerseusQuestion(widgets, {
        'dropdown 1': { value: 0 },
      });
      expect(result.correct).toBe(false);
    });

    it('null selection is incorrect', () => {
      const result = scorePerseusQuestion(widgets, {
        'dropdown 1': { value: null },
      });
      expect(result.correct).toBe(false);
    });

    it('uses "selected" key as fallback', () => {
      const result = scorePerseusQuestion(widgets, {
        'dropdown 1': { selected: 1 },
      });
      expect(result.correct).toBe(true);
    });
  });

  // ---------- expression ----------
  describe('expression', () => {
    const widgets = {
      'expression 1': {
        type: 'expression',
        options: {
          answerForms: [
            { value: '2x + 3', considered: 'correct' },
          ],
        },
      },
    };

    it('exact match', () => {
      const result = scorePerseusQuestion(widgets, {
        'expression 1': { currentValue: '2x + 3' },
      });
      expect(result.correct).toBe(true);
    });

    it('normalized match (extra whitespace)', () => {
      const result = scorePerseusQuestion(widgets, {
        'expression 1': { currentValue: '  2x+3  ' },
      });
      expect(result.correct).toBe(true);
    });

    it('wrong answer', () => {
      const result = scorePerseusQuestion(widgets, {
        'expression 1': { currentValue: '3x + 2' },
      });
      expect(result.correct).toBe(false);
    });

    it('empty input is incorrect', () => {
      const result = scorePerseusQuestion(widgets, {
        'expression 1': { currentValue: '' },
      });
      expect(result.correct).toBe(false);
    });

    it('whitespace-only input is incorrect', () => {
      const result = scorePerseusQuestion(widgets, {
        'expression 1': { currentValue: '   ' },
      });
      expect(result.correct).toBe(false);
    });

    it('string input format also works', () => {
      const result = scorePerseusQuestion(widgets, {
        'expression 1': '2x + 3',
      });
      expect(result.correct).toBe(true);
    });

    it('fraction normalization matches', () => {
      const fWidgets = {
        'expression 1': {
          type: 'expression',
          options: {
            answerForms: [
              { value: '\\frac{1}{2}', considered: 'correct' },
            ],
          },
        },
      };
      const result = scorePerseusQuestion(fWidgets, {
        'expression 1': { currentValue: '1/2' },
      });
      expect(result.correct).toBe(true);
    });
  });

  // ---------- orderer ----------
  describe('orderer', () => {
    const widgets = {
      'orderer 1': {
        type: 'orderer',
        options: {
          correctOptions: [
            { content: 'First' },
            { content: 'Second' },
            { content: 'Third' },
          ],
        },
      },
    };

    it('correct order', () => {
      const result = scorePerseusQuestion(widgets, {
        'orderer 1': { current: [{ content: 'First' }, { content: 'Second' }, { content: 'Third' }] },
      });
      expect(result.correct).toBe(true);
    });

    it('wrong order', () => {
      const result = scorePerseusQuestion(widgets, {
        'orderer 1': { current: [{ content: 'Third' }, { content: 'First' }, { content: 'Second' }] },
      });
      expect(result.correct).toBe(false);
    });

    it('partial (different length)', () => {
      const result = scorePerseusQuestion(widgets, {
        'orderer 1': { current: [{ content: 'First' }, { content: 'Second' }] },
      });
      expect(result.correct).toBe(false);
    });

    it('handles string-format items', () => {
      const result = scorePerseusQuestion(widgets, {
        'orderer 1': { current: ['First', 'Second', 'Third'] },
      });
      expect(result.correct).toBe(true);
    });

    it('handles string-format correct options', () => {
      const strWidgets = {
        'orderer 1': {
          type: 'orderer',
          options: {
            correctOptions: ['Alpha', 'Beta', 'Gamma'],
          },
        },
      };
      const result = scorePerseusQuestion(strWidgets, {
        'orderer 1': { current: ['Alpha', 'Beta', 'Gamma'] },
      });
      expect(result.correct).toBe(true);
    });
  });

  // ---------- matcher ----------
  describe('matcher', () => {
    const widgets = {
      'matcher 1': {
        type: 'matcher',
        options: {
          right: ['cat', 'dog', 'bird'],
        },
      },
    };

    it('all correct', () => {
      const result = scorePerseusQuestion(widgets, {
        'matcher 1': { right: ['cat', 'dog', 'bird'] },
      });
      expect(result.correct).toBe(true);
    });

    it('one wrong', () => {
      const result = scorePerseusQuestion(widgets, {
        'matcher 1': { right: ['cat', 'bird', 'dog'] },
      });
      expect(result.correct).toBe(false);
    });

    it('different lengths', () => {
      const result = scorePerseusQuestion(widgets, {
        'matcher 1': { right: ['cat', 'dog'] },
      });
      expect(result.correct).toBe(false);
    });

    it('empty user input', () => {
      const result = scorePerseusQuestion(widgets, {
        'matcher 1': { right: [] },
      });
      expect(result.correct).toBe(false);
    });
  });

  // ---------- sorter ----------
  describe('sorter', () => {
    const widgets = {
      'sorter 1': {
        type: 'sorter',
        options: {
          correct: ['A', 'B', 'C'],
        },
      },
    };

    it('correct order', () => {
      const result = scorePerseusQuestion(widgets, {
        'sorter 1': { options: ['A', 'B', 'C'] },
      });
      expect(result.correct).toBe(true);
    });

    it('wrong order', () => {
      const result = scorePerseusQuestion(widgets, {
        'sorter 1': { options: ['C', 'A', 'B'] },
      });
      expect(result.correct).toBe(false);
    });

    it('trimming differences still match', () => {
      const result = scorePerseusQuestion(widgets, {
        'sorter 1': { options: [' A ', ' B ', ' C '] },
      });
      expect(result.correct).toBe(true);
    });

    it('uses "current" key as fallback', () => {
      const result = scorePerseusQuestion(widgets, {
        'sorter 1': { current: ['A', 'B', 'C'] },
      });
      expect(result.correct).toBe(true);
    });

    it('different lengths', () => {
      const result = scorePerseusQuestion(widgets, {
        'sorter 1': { options: ['A', 'B'] },
      });
      expect(result.correct).toBe(false);
    });
  });

  // ---------- categorizer ----------
  describe('categorizer', () => {
    const widgets = {
      'categorizer 1': {
        type: 'categorizer',
        options: {
          values: [0, 1, 2, 1],
        },
      },
    };

    it('all correct', () => {
      const result = scorePerseusQuestion(widgets, {
        'categorizer 1': { values: [0, 1, 2, 1] },
      });
      expect(result.correct).toBe(true);
    });

    it('one wrong', () => {
      const result = scorePerseusQuestion(widgets, {
        'categorizer 1': { values: [0, 1, 2, 0] },
      });
      expect(result.correct).toBe(false);
    });

    it('null values in user input are incorrect', () => {
      const result = scorePerseusQuestion(widgets, {
        'categorizer 1': { values: [0, null, 2, 1] },
      });
      expect(result.correct).toBe(false);
    });

    it('different lengths are incorrect', () => {
      const result = scorePerseusQuestion(widgets, {
        'categorizer 1': { values: [0, 1] },
      });
      expect(result.correct).toBe(false);
    });
  });

  // ---------- number-line ----------
  describe('number-line', () => {
    const mkWidget = (correctX: number, correctRel: string, snapDivisions = 2, tickStep = 1) => ({
      'number-line 1': {
        type: 'number-line',
        options: { correctX, correctRel, snapDivisions, tickStep },
      },
    });

    it('eq: within tolerance', () => {
      // tolerance = tickStep/snap/2 = 1/2/2 = 0.25
      const result = scorePerseusQuestion(mkWidget(5, 'eq'), {
        'number-line 1': { numLinePosition: 5.2 },
      });
      expect(result.correct).toBe(true);
    });

    it('eq: outside tolerance', () => {
      const result = scorePerseusQuestion(mkWidget(5, 'eq'), {
        'number-line 1': { numLinePosition: 5.5 },
      });
      expect(result.correct).toBe(false);
    });

    it('lt: user value less than correct', () => {
      const result = scorePerseusQuestion(mkWidget(5, 'lt'), {
        'number-line 1': { numLinePosition: 3 },
      });
      expect(result.correct).toBe(true);
    });

    it('lt: user value greater than correct', () => {
      const result = scorePerseusQuestion(mkWidget(5, 'lt'), {
        'number-line 1': { numLinePosition: 6 },
      });
      expect(result.correct).toBe(false);
    });

    it('gt: user value greater than correct', () => {
      const result = scorePerseusQuestion(mkWidget(5, 'gt'), {
        'number-line 1': { numLinePosition: 7 },
      });
      expect(result.correct).toBe(true);
    });

    it('gt: user value less than correct', () => {
      const result = scorePerseusQuestion(mkWidget(5, 'gt'), {
        'number-line 1': { numLinePosition: 4 },
      });
      expect(result.correct).toBe(false);
    });

    it('le: user value at tolerance boundary', () => {
      // tolerance=0.25, correctX=5, so userX <= 5+0.25 = 5.25
      const result = scorePerseusQuestion(mkWidget(5, 'le'), {
        'number-line 1': { numLinePosition: 5.25 },
      });
      expect(result.correct).toBe(true);
    });

    it('le: user value beyond tolerance', () => {
      const result = scorePerseusQuestion(mkWidget(5, 'le'), {
        'number-line 1': { numLinePosition: 5.5 },
      });
      expect(result.correct).toBe(false);
    });

    it('ge: user value at tolerance boundary', () => {
      // tolerance=0.25, correctX=5, so userX >= 5-0.25 = 4.75
      const result = scorePerseusQuestion(mkWidget(5, 'ge'), {
        'number-line 1': { numLinePosition: 4.75 },
      });
      expect(result.correct).toBe(true);
    });

    it('ge: user value below boundary', () => {
      const result = scorePerseusQuestion(mkWidget(5, 'ge'), {
        'number-line 1': { numLinePosition: 4.5 },
      });
      expect(result.correct).toBe(false);
    });

    it('ne: user far from correct', () => {
      const result = scorePerseusQuestion(mkWidget(5, 'ne'), {
        'number-line 1': { numLinePosition: 8 },
      });
      expect(result.correct).toBe(true);
    });

    it('ne: user at correct value', () => {
      const result = scorePerseusQuestion(mkWidget(5, 'ne'), {
        'number-line 1': { numLinePosition: 5 },
      });
      expect(result.correct).toBe(false);
    });

    it('null userX is incorrect', () => {
      const result = scorePerseusQuestion(mkWidget(5, 'eq'), {
        'number-line 1': { numLinePosition: null },
      });
      expect(result.correct).toBe(false);
    });
  });

  // ---------- table ----------
  describe('table', () => {
    const widgets = {
      'table 1': {
        type: 'table',
        options: {
          answers: [
            ['1', '2', '3'],
            ['4', '5', '6'],
          ],
        },
      },
    };

    it('exact match', () => {
      const result = scorePerseusQuestion(widgets, {
        'table 1': { answers: [['1', '2', '3'], ['4', '5', '6']] },
      });
      expect(result.correct).toBe(true);
    });

    it('numeric tolerance (within 0.01)', () => {
      const result = scorePerseusQuestion(widgets, {
        'table 1': { answers: [['1.005', '2.005', '3'], ['4', '5', '6']] },
      });
      expect(result.correct).toBe(true);
    });

    it('numeric tolerance exceeded', () => {
      const result = scorePerseusQuestion(widgets, {
        'table 1': { answers: [['1.02', '2', '3'], ['4', '5', '6']] },
      });
      expect(result.correct).toBe(false);
    });

    it('case insensitive text match', () => {
      const textWidgets = {
        'table 1': {
          type: 'table',
          options: {
            answers: [['Hello', 'World']],
          },
        },
      };
      const result = scorePerseusQuestion(textWidgets, {
        'table 1': { answers: [['hello', 'world']] },
      });
      expect(result.correct).toBe(true);
    });

    it('wrong dimensions (too few rows)', () => {
      const result = scorePerseusQuestion(widgets, {
        'table 1': { answers: [['1', '2', '3']] },
      });
      expect(result.correct).toBe(false);
    });

    it('wrong dimensions (row length mismatch)', () => {
      const result = scorePerseusQuestion(widgets, {
        'table 1': { answers: [['1', '2'], ['4', '5', '6']] },
      });
      expect(result.correct).toBe(false);
    });
  });

  // ---------- image (skipped) ----------
  describe('image', () => {
    it('should be skipped (not scoreable)', () => {
      const widgets = {
        'image 1': { type: 'image', options: {} },
      };
      const result = scorePerseusQuestion(widgets, {
        'image 1': {},
      });
      expect(result.scoreableCount).toBe(0);
      expect(result.correct).toBe(false); // no scoreable widgets = not correct
    });
  });

  // ---------- definition (skipped) ----------
  describe('definition', () => {
    it('should be skipped (not scoreable)', () => {
      const widgets = {
        'definition 1': { type: 'definition', options: {} },
      };
      const result = scorePerseusQuestion(widgets, {
        'definition 1': {},
      });
      expect(result.scoreableCount).toBe(0);
      expect(result.correct).toBe(false);
    });
  });

  // ---------- multi-widget ----------
  describe('multi-widget', () => {
    it('both correct widgets -> correct', () => {
      const widgets = {
        'radio 1': {
          type: 'radio',
          options: {
            choices: [
              { content: 'Wrong', correct: false },
              { content: 'Right', correct: true },
            ],
            multipleSelect: false,
          },
        },
        'numeric-input 1': {
          type: 'numeric-input',
          options: {
            answers: [{ status: 'correct', value: 42, maxError: 0.5 }],
          },
        },
      };
      const result = scorePerseusQuestion(widgets, {
        'radio 1': { selectedChoiceIds: ['choice-1'] },
        'numeric-input 1': { currentValue: '42' },
      });
      expect(result.correct).toBe(true);
      expect(result.scoreableCount).toBe(2);
      expect(result.correctCount).toBe(2);
    });

    it('one correct, one wrong -> incorrect', () => {
      const widgets = {
        'radio 1': {
          type: 'radio',
          options: {
            choices: [
              { content: 'Wrong', correct: false },
              { content: 'Right', correct: true },
            ],
            multipleSelect: false,
          },
        },
        'numeric-input 1': {
          type: 'numeric-input',
          options: {
            answers: [{ status: 'correct', value: 42, maxError: 0.5 }],
          },
        },
      };
      const result = scorePerseusQuestion(widgets, {
        'radio 1': { selectedChoiceIds: ['choice-1'] },
        'numeric-input 1': { currentValue: '99' },
      });
      expect(result.correct).toBe(false);
      expect(result.scoreableCount).toBe(2);
      expect(result.correctCount).toBe(1);
    });

    it('image widget ignored alongside scoreable widget', () => {
      const widgets = {
        'image 1': { type: 'image', options: {} },
        'radio 1': {
          type: 'radio',
          options: {
            choices: [{ content: 'Right', correct: true }],
            multipleSelect: false,
          },
        },
      };
      const result = scorePerseusQuestion(widgets, {
        'image 1': {},
        'radio 1': { selectedChoiceIds: ['choice-0'] },
      });
      expect(result.correct).toBe(true);
      expect(result.scoreableCount).toBe(1);
    });
  });

  // ---------- edge cases ----------
  describe('edge cases', () => {
    it('no matching widget definitions -> no scoreable', () => {
      const result = scorePerseusQuestion({}, {
        'radio 1': { selectedChoiceIds: ['choice-0'] },
      });
      expect(result.correct).toBe(false);
      expect(result.scoreableCount).toBe(0);
    });

    it('empty user input -> no scoreable', () => {
      const result = scorePerseusQuestion({
        'radio 1': { type: 'radio', options: { choices: [{ correct: true }] } },
      }, {});
      expect(result.correct).toBe(false);
      expect(result.scoreableCount).toBe(0);
    });
  });
});

// ============================================================================
// hasUserInput()
// ============================================================================

describe('hasUserInput', () => {

  describe('radio', () => {
    const widgets = { 'radio 1': { type: 'radio' } };

    it('returns true with selections', () => {
      expect(hasUserInput(widgets, { 'radio 1': { selectedChoiceIds: ['choice-0'] } })).toBe(true);
    });
    it('returns false with empty array', () => {
      expect(hasUserInput(widgets, { 'radio 1': { selectedChoiceIds: [] } })).toBe(false);
    });
    it('returns false with missing selectedChoiceIds', () => {
      expect(hasUserInput(widgets, { 'radio 1': {} })).toBe(false);
    });
  });

  describe('numeric-input', () => {
    const widgets = { 'numeric-input 1': { type: 'numeric-input' } };

    it('returns true with a value', () => {
      expect(hasUserInput(widgets, { 'numeric-input 1': { currentValue: '42' } })).toBe(true);
    });
    it('returns false with empty string', () => {
      expect(hasUserInput(widgets, { 'numeric-input 1': { currentValue: '' } })).toBe(false);
    });
    it('returns false with null', () => {
      expect(hasUserInput(widgets, { 'numeric-input 1': { currentValue: null } })).toBe(false);
    });
  });

  describe('expression', () => {
    const widgets = { 'expression 1': { type: 'expression' } };

    it('returns true with an expression', () => {
      expect(hasUserInput(widgets, { 'expression 1': { currentValue: '2x+3' } })).toBe(true);
    });
    it('returns true with string-format input', () => {
      expect(hasUserInput(widgets, { 'expression 1': '2x+3' })).toBe(true);
    });
    it('returns false with empty string', () => {
      expect(hasUserInput(widgets, { 'expression 1': { currentValue: '' } })).toBe(false);
    });
    it('returns false with whitespace-only', () => {
      expect(hasUserInput(widgets, { 'expression 1': { currentValue: '   ' } })).toBe(false);
    });
  });

  describe('dropdown', () => {
    const widgets = { 'dropdown 1': { type: 'dropdown' } };

    it('returns true with index 0 (valid choice)', () => {
      expect(hasUserInput(widgets, { 'dropdown 1': { value: 0 } })).toBe(true);
    });
    it('returns true with a positive index', () => {
      expect(hasUserInput(widgets, { 'dropdown 1': { value: 2 } })).toBe(true);
    });
    it('returns false with null', () => {
      expect(hasUserInput(widgets, { 'dropdown 1': { value: null } })).toBe(false);
    });
    it('returns true with "selected" key', () => {
      expect(hasUserInput(widgets, { 'dropdown 1': { selected: 1 } })).toBe(true);
    });
    it('returns false with negative index', () => {
      expect(hasUserInput(widgets, { 'dropdown 1': { value: -1 } })).toBe(false);
    });
  });

  describe('orderer', () => {
    const widgets = { 'orderer 1': { type: 'orderer' } };

    it('returns true with items', () => {
      expect(hasUserInput(widgets, { 'orderer 1': { current: ['a', 'b'] } })).toBe(true);
    });
    it('returns false with empty array', () => {
      expect(hasUserInput(widgets, { 'orderer 1': { current: [] } })).toBe(false);
    });
  });

  describe('matcher', () => {
    const widgets = { 'matcher 1': { type: 'matcher' } };

    it('returns true with items', () => {
      expect(hasUserInput(widgets, { 'matcher 1': { right: ['a', 'b'] } })).toBe(true);
    });
    it('returns false with empty array', () => {
      expect(hasUserInput(widgets, { 'matcher 1': { right: [] } })).toBe(false);
    });
  });

  describe('sorter', () => {
    const widgets = { 'sorter 1': { type: 'sorter' } };

    it('returns true with "options" key', () => {
      expect(hasUserInput(widgets, { 'sorter 1': { options: ['a', 'b'] } })).toBe(true);
    });
    it('returns true with "current" key', () => {
      expect(hasUserInput(widgets, { 'sorter 1': { current: ['a', 'b'] } })).toBe(true);
    });
    it('returns false with empty arrays', () => {
      expect(hasUserInput(widgets, { 'sorter 1': { options: [], current: [] } })).toBe(false);
    });
  });

  describe('categorizer', () => {
    const widgets = { 'categorizer 1': { type: 'categorizer' } };

    it('returns true with valid values', () => {
      expect(hasUserInput(widgets, { 'categorizer 1': { values: [0, 1, 2] } })).toBe(true);
    });
    it('returns false with empty array', () => {
      expect(hasUserInput(widgets, { 'categorizer 1': { values: [] } })).toBe(false);
    });
    it('returns false with all null values', () => {
      expect(hasUserInput(widgets, { 'categorizer 1': { values: [null, null] } })).toBe(false);
    });
    it('returns false with all negative values', () => {
      expect(hasUserInput(widgets, { 'categorizer 1': { values: [-1, -1] } })).toBe(false);
    });
  });

  describe('number-line', () => {
    const widgets = { 'number-line 1': { type: 'number-line' } };

    it('returns true with a position', () => {
      expect(hasUserInput(widgets, { 'number-line 1': { numLinePosition: 5 } })).toBe(true);
    });
    it('returns true with position 0', () => {
      expect(hasUserInput(widgets, { 'number-line 1': { numLinePosition: 0 } })).toBe(true);
    });
    it('returns false with null position', () => {
      expect(hasUserInput(widgets, { 'number-line 1': { numLinePosition: null } })).toBe(false);
    });
  });

  describe('table', () => {
    const widgets = { 'table 1': { type: 'table' } };

    it('returns true with filled cells', () => {
      expect(hasUserInput(widgets, { 'table 1': { answers: [['1', '2']] } })).toBe(true);
    });
    it('returns false with all empty cells', () => {
      expect(hasUserInput(widgets, { 'table 1': { answers: [['', '']] } })).toBe(false);
    });
    it('returns false with empty rows', () => {
      expect(hasUserInput(widgets, { 'table 1': { answers: [] } })).toBe(false);
    });
  });

  describe('image (skipped)', () => {
    it('returns false for image widget', () => {
      expect(hasUserInput(
        { 'image 1': { type: 'image' } },
        { 'image 1': { url: 'something' } },
      )).toBe(false);
    });
  });

  describe('definition (skipped)', () => {
    it('returns false for definition widget', () => {
      expect(hasUserInput(
        { 'definition 1': { type: 'definition' } },
        { 'definition 1': { content: 'something' } },
      )).toBe(false);
    });
  });

  describe('unknown widget with no match', () => {
    it('returns false when widget def not found', () => {
      expect(hasUserInput({}, { 'radio 1': { selectedChoiceIds: ['choice-0'] } })).toBe(false);
    });
  });
});
