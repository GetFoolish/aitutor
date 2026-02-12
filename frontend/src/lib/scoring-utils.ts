/**
 * Shared scoring utilities for Perseus-format questions.
 *
 * Used by both RendererComponent (practice mode) and AssessmentQuestion (assessment mode)
 * to ensure consistent scoring across all 9 widget types.
 */

// ---------------------------------------------------------------------------
// Expression normalization
// ---------------------------------------------------------------------------

/**
 * Deep-normalize a math expression for comparison.
 * Handles: whitespace, LaTeX wrappers, fractions, multiplication symbols,
 * commutativity of addition, trivial parentheses, simple exponents, integer division.
 */
export function deepNormalize(s: string): string {
    let n = s.replace(/\s+/g, '').toLowerCase();
    // Normalize Unicode multiplication symbols: × (U+00D7), · (U+00B7)
    n = n.replace(/[×·]/g, '*');
    // Strip LaTeX wrappers: \text{}, \mathrm{}, etc.
    n = n.replace(/\\(?:text|mathrm|mathit)\{([^}]*)\}/g, '$1');
    // Convert \frac{a}{b} to (a)/(b) for comparison
    n = n.replace(/\\frac\{([^}]*)\}\{([^}]*)\}/g, '($1)/($2)');
    // Normalize multiplication: \cdot, \times → *
    n = n.replace(/[\\](?:cdot|times)/g, '*');
    // Remove braces that are just grouping: {x} → x (loop for nested braces)
    while (/\{([^{}]+)\}/.test(n)) {
        n = n.replace(/\{([^{}]+)\}/g, '$1');
    }
    // Strip trivial parentheses around single tokens: (2) → 2, ((x)) → x
    while (/\((\w+)\)/.test(n)) {
        n = n.replace(/\((\w+)\)/g, '$1');
    }
    // Evaluate simple integer exponents: 2^3 → 8 (only safe small values)
    n = n.replace(/(\d+)\^(\d+)/g, (match, base, exp) => {
        const result = Math.pow(parseInt(base), parseInt(exp));
        return Number.isInteger(result) && result < 1e6 ? String(result) : match;
    });
    // Evaluate simple integer division when it's the entire expression: 6/3 → 2
    if (/^\d+\/\d+$/.test(n)) {
        const [num, den] = n.split('/').map(Number);
        if (den !== 0 && Number.isInteger(num / den)) {
            n = String(num / den);
        }
    }
    // Sort additive terms for commutativity: "7+x" and "x+7" both become the same
    // Only sort when ALL terms are additive (no subtraction) to avoid "5-3" ≠ "3-5" bug
    const terms = n.split(/(?=[+-])/);
    const hasSubtraction = terms.some(t => t.startsWith('-'));
    const hasMultiplication = terms.some(t => /[*^]/.test(t));
    if (terms.length > 1 && !hasSubtraction && !hasMultiplication && !n.includes('(') && !n.includes('/')) {
        n = terms.sort().join('');
    }
    return n;
}

// ---------------------------------------------------------------------------
// Per-widget scoring
// ---------------------------------------------------------------------------

export interface ScoringResult {
    correct: boolean;
    scoreableCount: number;
    correctCount: number;
    /** Text of the selected answer (first scoreable widget), for analytics */
    selectedAnswerText: string;
    /** Index of the selected answer (radio/dropdown), for analytics */
    selectedAnswerIndex: number | null;
}

/**
 * Score a Perseus-format question against user input.
 *
 * AND logic: ALL scoreable widgets must be correct for the question to be correct.
 * Display-only widgets (image, definition) are skipped.
 */
export function scorePerseusQuestion(
    questionWidgets: Record<string, any>,
    userInput: Record<string, any>,
): ScoringResult {
    let scoreableCount = 0;
    let correctCount = 0;
    let selectedAnswerText = '';
    let selectedAnswerIndex: number | null = null;

    for (const [widgetId, widgetInput] of Object.entries(userInput)) {
        const widgetDef = questionWidgets?.[widgetId];
        if (!widgetDef) continue;
        // Skip display-only widgets (image only — definition has a companion radio that IS scored)
        if (widgetDef.type === 'image') continue;

        let widgetCorrect = false;

        if (widgetDef.type === 'radio') {
            const choices = widgetDef.options?.choices || [];
            const selectedIds = (widgetInput as any).selectedChoiceIds || [];
            const isMultiSelect = widgetDef.options?.multipleSelect || false;

            if (isMultiSelect) {
                const correctIndices = choices
                    .map((c: any, i: number) => c.correct ? i : -1)
                    .filter((i: number) => i >= 0);
                const selectedIndices = selectedIds.map((id: string) => {
                    const match = id.match(/choice-(\d+)/);
                    return match ? parseInt(match[1]) : -1;
                }).filter((i: number) => i >= 0);
                // Bidirectional check: selected must match correct exactly (no over-selecting)
                widgetCorrect = correctIndices.length === selectedIndices.length &&
                    correctIndices.every((idx: number) => selectedIndices.includes(idx)) &&
                    selectedIndices.every((idx: number) => correctIndices.includes(idx));
            } else {
                if (selectedIds.length === 1) {
                    const match = selectedIds[0].match(/choice-(\d+)/);
                    if (match) {
                        const idx = parseInt(match[1]);
                        widgetCorrect = choices[idx]?.correct === true;
                        if (!selectedAnswerText) {
                            selectedAnswerText = choices[idx]?.content || '';
                            selectedAnswerIndex = idx;
                        }
                    }
                }
            }
            scoreableCount++;
            if (widgetCorrect) correctCount++;

        } else if (widgetDef.type === 'definition') {
            // Definition widget is display-only — skip scoring (companion radio is scored separately)
            continue;

        } else if (widgetDef.type === 'orderer') {
            const correctOptions = widgetDef.options?.correctOptions || [];
            const userOrder = (widgetInput as any).current || [];
            if (correctOptions.length === userOrder.length) {
                widgetCorrect = correctOptions.every((correctOpt: any, index: number) => {
                    const userItem = userOrder[index];
                    const userContent = (typeof userItem === 'string' ? userItem : userItem?.content || '').trim();
                    const correctContent = (typeof correctOpt === 'string' ? correctOpt : correctOpt?.content || '').trim();
                    return correctContent === userContent;
                });
            }
            scoreableCount++;
            if (widgetCorrect) correctCount++;

        } else if (widgetDef.type === 'numeric-input') {
            const answers = widgetDef.options?.answers || [];
            const userValue = parseFloat((widgetInput as any)?.currentValue || '');
            if (!selectedAnswerText) {
                selectedAnswerText = (widgetInput as any)?.currentValue || '';
            }
            if (!isNaN(userValue) && answers.length > 0) {
                const correctAnswer = answers.find((a: any) => a.status === 'correct');
                if (correctAnswer) {
                    let maxError = correctAnswer.maxError;
                    if (maxError == null || maxError <= 0) {
                        const cv = correctAnswer.value;
                        if (cv === 0) {
                            maxError = 0.001;
                        } else {
                            // Use 1% of absolute value, with a floor of 0.01
                            maxError = Math.max(0.01, Math.abs(cv) * 0.01);
                        }
                    }
                    widgetCorrect = Math.abs(userValue - correctAnswer.value) <= maxError;
                }
            }
            scoreableCount++;
            if (widgetCorrect) correctCount++;

        } else if (widgetDef.type === 'dropdown') {
            const choices = widgetDef.options?.choices || [];
            const selectedIdx = (widgetInput as any)?.value ?? (widgetInput as any)?.selected;
            if (selectedIdx != null && selectedIdx >= 0 && selectedIdx < choices.length) {
                widgetCorrect = choices[selectedIdx]?.correct === true;
                if (!selectedAnswerText) {
                    selectedAnswerText = choices[selectedIdx]?.content || '';
                    selectedAnswerIndex = selectedIdx;
                }
            }
            scoreableCount++;
            if (widgetCorrect) correctCount++;

        } else if (widgetDef.type === 'expression') {
            const answerForms = widgetDef.options?.answerForms || [];
            const userExpr = typeof widgetInput === 'string'
                ? widgetInput
                : ((widgetInput as any)?.currentValue || '');
            if (userExpr && userExpr.trim() && answerForms.length > 0) {
                const userNorm = deepNormalize(userExpr);
                widgetCorrect = answerForms.some((f: any) =>
                    f.considered === 'correct' && deepNormalize(f.value || '') === userNorm
                );
            }
            scoreableCount++;
            if (widgetCorrect) correctCount++;

        } else if (widgetDef.type === 'matcher') {
            const correctRight = widgetDef.options?.right || [];
            const userRight = (widgetInput as any)?.right || [];
            if (correctRight.length > 0 && correctRight.length === userRight.length) {
                widgetCorrect = correctRight.every((val: string, idx: number) => val === userRight[idx]);
            }
            scoreableCount++;
            if (widgetCorrect) correctCount++;

        } else if (widgetDef.type === 'sorter') {
            const correctOrder = widgetDef.options?.correct || [];
            const userOrder = (widgetInput as any)?.options || (widgetInput as any)?.current || [];
            if (correctOrder.length > 0 && correctOrder.length === userOrder.length) {
                widgetCorrect = correctOrder.every((val: string, idx: number) => {
                    const cv = (typeof val === 'string' ? val : '').trim();
                    const uv = (typeof userOrder[idx] === 'string' ? userOrder[idx] : '').trim();
                    return cv === uv;
                });
            }
            scoreableCount++;
            if (widgetCorrect) correctCount++;

        } else if (widgetDef.type === 'categorizer') {
            const correctValues: number[] = widgetDef.options?.values || [];
            const userValues: number[] = (widgetInput as any)?.values || [];
            if (correctValues.length > 0 && correctValues.length === userValues.length) {
                widgetCorrect = correctValues.every((val: number, idx: number) =>
                    userValues[idx] != null && val === userValues[idx]
                );
            }
            scoreableCount++;
            if (widgetCorrect) correctCount++;

        } else if (widgetDef.type === 'number-line') {
            const correctX = widgetDef.options?.correctX;
            const correctRel = widgetDef.options?.correctRel || 'eq';
            const userX = (widgetInput as any)?.numLinePosition;
            if (correctX != null && userX != null) {
                const snap = widgetDef.options?.snapDivisions || 2;
                const tickStep = widgetDef.options?.tickStep || 1;
                const tolerance = tickStep / snap / 2;  // half a snap step
                switch (correctRel) {
                    case 'eq':
                        widgetCorrect = Math.abs(userX - correctX) <= tolerance;
                        break;
                    case 'lt':
                        widgetCorrect = userX < correctX;
                        break;
                    case 'gt':
                        widgetCorrect = userX > correctX;
                        break;
                    case 'le':
                        widgetCorrect = userX <= correctX + tolerance;
                        break;
                    case 'ge':
                        widgetCorrect = userX >= correctX - tolerance;
                        break;
                    case 'ne':
                        widgetCorrect = Math.abs(userX - correctX) > tolerance;
                        break;
                    default:
                        widgetCorrect = Math.abs(userX - correctX) <= tolerance;
                }
            }
            scoreableCount++;
            if (widgetCorrect) correctCount++;

        } else if (widgetDef.type === 'table') {
            const correctAnswers: string[][] = widgetDef.options?.answers || [];
            const userAnswers: string[][] = (widgetInput as any)?.answers || [];
            if (correctAnswers.length > 0 && correctAnswers.length === userAnswers.length) {
                widgetCorrect = correctAnswers.every((row: string[], rIdx: number) =>
                    row.length === (userAnswers[rIdx]?.length || 0) &&
                    row.every((cell: string, cIdx: number) => {
                        const userCell = (userAnswers[rIdx]?.[cIdx] || '').trim();
                        const correctCell = cell.trim();
                        // Try numeric comparison first
                        const numUser = parseFloat(userCell);
                        const numCorrect = parseFloat(correctCell);
                        if (!isNaN(numUser) && !isNaN(numCorrect)) {
                            return Math.abs(numUser - numCorrect) < 0.01;
                        }
                        return userCell.toLowerCase() === correctCell.toLowerCase();
                    })
                );
            }
            scoreableCount++;
            if (widgetCorrect) correctCount++;
        }
    }

    return {
        correct: scoreableCount > 0 && correctCount === scoreableCount,
        scoreableCount,
        correctCount,
        selectedAnswerText,
        selectedAnswerIndex,
    };
}

// ---------------------------------------------------------------------------
// Input presence check (for empty submission guard)
// ---------------------------------------------------------------------------

/**
 * Check if the user has provided any input in scoreable widgets.
 * Returns true if at least one scoreable widget has user input.
 */
export function hasUserInput(
    questionWidgets: Record<string, any>,
    userInput: Record<string, any>,
): boolean {
    for (const [widgetId, widgetInput] of Object.entries(userInput)) {
        const widgetDef = questionWidgets?.[widgetId];
        if (!widgetDef) continue;
        if (widgetDef.type === 'image') continue;

        // Definition widget itself is display-only — skip it in input check
        // (its companion radio widget will be checked separately)
        if (widgetDef.type === 'definition') continue;

        if (widgetDef.type === 'radio') {
            if (((widgetInput as any).selectedChoiceIds || []).length > 0) return true;
        } else if (widgetDef.type === 'numeric-input') {
            const val = (widgetInput as any)?.currentValue;
            if (val != null && val !== '') return true;
        } else if (widgetDef.type === 'expression') {
            const val = typeof widgetInput === 'string'
                ? widgetInput
                : ((widgetInput as any)?.currentValue || '');
            if (val && val.trim()) return true;
        } else if (widgetDef.type === 'dropdown') {
            const idx = (widgetInput as any)?.value ?? (widgetInput as any)?.selected;
            // Any non-null selection counts as real input (index 0 can be a valid choice)
            if (idx != null && idx >= 0) return true;
        } else if (widgetDef.type === 'orderer') {
            const curr = (widgetInput as any)?.current || [];
            if (curr.length > 0) return true;
        } else if (widgetDef.type === 'matcher') {
            const right = (widgetInput as any)?.right || [];
            if (right.length > 0) return true;
        } else if (widgetDef.type === 'sorter') {
            const opts = (widgetInput as any)?.options || (widgetInput as any)?.current || [];
            if (opts.length > 0) return true;
        } else if (widgetDef.type === 'categorizer') {
            const vals = (widgetInput as any)?.values || [];
            if (vals.length > 0 && vals.some((v: any) => v != null && v >= 0)) return true;
        } else if (widgetDef.type === 'number-line') {
            const pos = (widgetInput as any)?.numLinePosition;
            if (pos != null) return true;
        } else if (widgetDef.type === 'table') {
            const answers = (widgetInput as any)?.answers || [];
            if (answers.some((row: any[]) => row?.some((cell: string) => cell && cell.trim()))) return true;
        }
    }
    return false;
}
