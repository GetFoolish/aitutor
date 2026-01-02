
const text = `Bailey Bear could not help himself and reached right into a beehive to get some honey. Ouch! Now he has bee stings all over. Create a bar graph to show how many bee stings he has on each leg and arm.

Body part | Number of bee stings |
:- | :-: | -
Right arm | $10$ |
Right leg |$2$ |
Left arm | $8$ |
Left leg | $4$ |

[[☃ plotter 1]]`;

// Mock processTable logic from AthenaRenderer
const processTable = (text) => {
    if (!text || typeof text !== 'string') return text || '';

    const lines = text.split('\n');
    const result = [];
    let i = 0;

    const isValidTableRow = (line) => {
        const trimmed = line.trim();
        if (trimmed.length < 5) return false;
        if (/^[\s|:\-]+$/.test(trimmed) && !trimmed.includes('|---|')) return false;
        if (/^\|+$/.test(trimmed.replace(/\s/g, ''))) return false;
        return true;
    };

    const processCellContent = (cell) => {
        let processed = cell;
        return processed;
    };

    const parseCells = (line) => {
        const trimmed = line.trim();
        if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
            return trimmed.slice(1, -1).split('|').map(c => c.trim());
        }
        if (trimmed.startsWith('|')) {
            return trimmed.slice(1).split('|').map(c => c.trim());
        }
        return trimmed.split('|').map(c => c.trim());
    };

    while (i < lines.length) {
        const line = lines[i];
        const trimmedLine = line.trim();
        const hasPipes = trimmedLine.includes('|');
        const isValid = isValidTableRow(trimmedLine);
        const cells = parseCells(trimmedLine);
        const hasMeaningful = cells.some(cell => cell.length > 0 && !/^[-:]+$/.test(cell));

        if (hasPipes && isValid && cells.length >= 2 && hasMeaningful) {
            const tableLines = [];
            let j = i;
            // Simplified collection logic
            let emptyLineCount = 0;
            while (j < lines.length) {
                const nextLine = lines[j].trim();
                if (nextLine.includes('|')) {
                    tableLines.push(lines[j]);
                    emptyLineCount = 0;
                    j++;
                } else if (nextLine === '') {
                    emptyLineCount++;
                    j++;
                    if (emptyLineCount > 1) break;
                } else {
                    break;
                }
            }

            // Render table
            if (tableLines.length >= 2) {
                let html = '<table class="athena-equation-table">';
                // Basic separator logic
                const separatorIndex = tableLines.findIndex(l => /^[\s|:\-]+$/.test(l.trim()) && l.includes('-'));

                if (separatorIndex >= 0) {
                    html += '<thead>';
                    // ... headers ...
                    html += '</thead><tbody>';
                    // ... body ...
                    html += '</tbody>';
                }
                html += '</table>';

                result.push(html);
                i = j;
                continue;
            }
        }
        result.push(line);
        i++;
    }
    return result.join('\n');
};

console.log(processTable(text));
