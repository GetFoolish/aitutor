/**
 * Demo Widgets for Side-by-Side Comparison
 *
 * All 34 widget types formatted as AthenaItem for testing.
 */

import type { AthenaItem } from '../../services/sherlockedAPI_New';

// Demo widgets type - uses type assertion since demo data doesn't have all required fields
// At runtime these are compatible with what the renderers expect
export const DEMO_WIDGETS = [
  // 1. numeric-input
  {
    _id: 'demo-numeric-input',
    widgetTypes: ['numeric-input'],
    question: {
      content: 'Solve: **3x + 7 = 22**\n\nWhat is the value of x?\n\n[[☃ numeric-input 1]]',
      widgets: {
        'numeric-input 1': {
          type: 'numeric-input',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            answers: [{ value: 5, status: 'correct', maxError: 0 }],
            size: 'normal',
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 2. radio
  {
    _id: 'demo-radio',
    widgetTypes: ['radio'],
    question: {
      content: 'Which expression equals **x³ · x⁴**?\n\n[[☃ radio 1]]',
      widgets: {
        'radio 1': {
          type: 'radio',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            choices: [
              { content: '$x^7$', correct: true },
              { content: '$x^{12}$', correct: false },
              { content: '$x^1$', correct: false },
              { content: '$2x^7$', correct: false },
            ],
            randomize: false,
            multipleSelect: false,
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 3. dropdown
  {
    _id: 'demo-dropdown',
    widgetTypes: ['dropdown'],
    question: {
      content: 'Water at room temperature is in what state? [[☃ dropdown 1]]',
      widgets: {
        'dropdown 1': {
          type: 'dropdown',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            choices: [
              { content: 'Liquid', correct: true },
              { content: 'Solid', correct: false },
              { content: 'Gas', correct: false },
              { content: 'Plasma', correct: false },
            ],
            placeholder: 'Select a state',
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 4. expression
  {
    _id: 'demo-expression',
    widgetTypes: ['expression'],
    question: {
      content: 'Simplify: **(x² - 4) / (x + 2)**\n\n[[☃ expression 1]]',
      widgets: {
        'expression 1': {
          type: 'expression',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            answerForms: [{ value: 'x-2', form: true, simplify: true, considered: 'correct' }],
            buttonSets: ['basic', 'algebra'],
            functions: [],
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 5. input-number
  {
    _id: 'demo-input-number',
    widgetTypes: ['input-number'],
    question: {
      content: 'Calculate: **144 ÷ 12 = ?**\n\n[[☃ input-number 1]]',
      widgets: {
        'input-number 1': {
          type: 'input-number',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            value: 12,
            simplify: 'required',
            size: 'normal',
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 6. passage
  {
    _id: 'demo-passage',
    widgetTypes: ['passage'],
    question: {
      content: 'Read the following excerpt:\n\n[[☃ passage 1]]',
      widgets: {
        'passage 1': {
          type: 'passage',
          alignment: 'default',
          static: true,
          graded: false,
          options: {
            passageTitle: 'Declaration of Independence (1776)',
            passageText: 'We hold these truths to be self-evident, that all men are created equal, that they are endowed by their Creator with certain unalienable Rights, that among these are Life, Liberty and the pursuit of Happiness.',
            showLineNumbers: true,
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 7. image
  {
    _id: 'demo-image',
    widgetTypes: ['image'],
    question: {
      content: 'The pie chart shows survey results.\n\n[[☃ image 1]]\n\nWhat percentage is shown in blue?',
      widgets: {
        'image 1': {
          type: 'image',
          alignment: 'block',
          static: true,
          graded: false,
          options: {
            alt: 'Pie chart showing 72% blue, 28% orange',
            backgroundImage: {
              url: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200'%3E%3Ccircle cx='100' cy='100' r='80' fill='%23e5e7eb'/%3E%3Cpath d='M100,100 L100,20 A80,80 0 1,1 38.4,159.6 Z' fill='%233b82f6'/%3E%3Ccircle cx='100' cy='100' r='40' fill='white'/%3E%3Ctext x='100' y='105' text-anchor='middle' font-size='18' font-weight='bold'%3E72%25%3C/text%3E%3C/svg%3E",
              width: 200,
              height: 200,
            },
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 8. video
  {
    _id: 'demo-video',
    widgetTypes: ['video'],
    question: {
      content: 'Watch this video about photosynthesis:\n\n[[☃ video 1]]',
      widgets: {
        'video 1': {
          type: 'video',
          alignment: 'block',
          static: true,
          graded: false,
          options: {
            location: 'https://www.youtube.com/embed/dQw4w9WgXcQ',
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 9. definition
  {
    _id: 'demo-definition',
    widgetTypes: ['definition'],
    question: {
      content: 'The process of [[☃ definition 1]] converts light into chemical energy.',
      widgets: {
        'definition 1': {
          type: 'definition',
          alignment: 'inline',
          static: true,
          graded: false,
          options: {
            togglePrompt: 'photosynthesis',
            definition: 'The process by which green plants use sunlight to synthesize nutrients from carbon dioxide and water.',
            static: false,
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 10. explanation
  {
    _id: 'demo-explanation',
    widgetTypes: ['explanation'],
    question: {
      content: 'Solve the quadratic equation: **x² + 5x + 6 = 0**\n\n[[☃ explanation 1]]',
      widgets: {
        'explanation 1': {
          type: 'explanation',
          alignment: 'default',
          static: true,
          graded: false,
          options: {
            showPrompt: 'Show solution steps',
            hidePrompt: 'Hide solution steps',
            explanation: 'Factor: (x + 2)(x + 3) = 0\n\nSolutions: **x = -2** or **x = -3**',
            widgets: {},
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 11. interactive-graph
  {
    _id: 'demo-interactive-graph',
    widgetTypes: ['interactive-graph'],
    question: {
      content: 'Plot the point **(2, 3)** on the graph:\n\n[[☃ interactive-graph 1]]',
      widgets: {
        'interactive-graph 1': {
          type: 'interactive-graph',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            range: [[-5, 5], [-5, 5]],
            step: [1, 1],
            gridStep: [1, 1],
            snapStep: [1, 1],
            graph: { type: 'point', numPoints: 1 },
            markings: 'graph',
            correct: { type: 'point', coords: [[2, 3]] },
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 12. grapher
  {
    _id: 'demo-grapher',
    widgetTypes: ['grapher'],
    question: {
      content: 'Graph the function **f(x) = x²**\n\n[[☃ grapher 1]]',
      widgets: {
        'grapher 1': {
          type: 'grapher',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            range: [[-5, 5], [-5, 5]],
            step: [1, 1],
            graph: { type: 'quadratic' },
            correct: { type: 'quadratic', coords: [[0, 0], [1, 1], [-1, 1]] },
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 13. plotter
  {
    _id: 'demo-plotter',
    widgetTypes: ['plotter'],
    question: {
      content: 'Plot the data points: (1, 2), (2, 4), (3, 6)\n\n[[☃ plotter 1]]',
      widgets: {
        'plotter 1': {
          type: 'plotter',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            range: [[0, 5], [0, 8]],
            step: [1, 1],
            starting: [],
            correct: [[1, 2], [2, 4], [3, 6]],
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 14. plotter (bar chart)
  {
    _id: 'demo-plotter-bar',
    widgetTypes: ['plotter'],
    question: {
      content: 'Create a bar chart for the data:\n\n[[☃ plotter 1]]',
      widgets: {
        'plotter 1': {
          type: 'plotter',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            range: [[0, 4], [0, 10]],
            categories: ['Apples', 'Oranges', 'Bananas', 'Grapes'],
            starting: [3, 5, 2, 7],
            maxY: 10,
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 15. number-line
  {
    _id: 'demo-number-line',
    widgetTypes: ['number-line'],
    question: {
      content: 'Place a point at **-2.5** on the number line:\n\n[[☃ number-line 1]]',
      widgets: {
        'number-line 1': {
          type: 'number-line',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            range: [-5, 5],
            numDivisions: 10,
            snapDivisions: 2,
            tickStep: 1,
            labelRange: [-5, 5],
            labelStyle: 'decimal',
            labelTicks: true,
            correctX: -2.5,
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 16. table
  {
    _id: 'demo-table',
    widgetTypes: ['table'],
    question: {
      content: 'Complete the table for **y = 2x**:\n\n[[☃ table 1]]',
      widgets: {
        'table 1': {
          type: 'table',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            headers: ['x', 'y = 2x'],
            rows: 4,
            columns: 2,
            answers: [['1', '2'], ['2', '4'], ['3', '6'], ['4', '8']],
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 17. categorizer
  {
    _id: 'demo-categorizer',
    widgetTypes: ['categorizer'],
    question: {
      content: 'Classify these animals into their correct groups:\n\n[[☃ categorizer 1]]',
      widgets: {
        'categorizer 1': {
          type: 'categorizer',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            categories: ['Mammals', 'Reptiles', 'Birds'],
            items: ['Dolphin', 'Snake', 'Eagle', 'Bat', 'Turtle', 'Penguin'],
            values: [0, 1, 2, 0, 1, 2],
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 18. sorter
  {
    _id: 'demo-sorter',
    widgetTypes: ['sorter'],
    question: {
      content: 'Order these fractions from **smallest to largest**:\n\n[[☃ sorter 1]]',
      widgets: {
        'sorter 1': {
          type: 'sorter',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            correct: ['1/4', '1/3', '1/2', '2/3', '3/4'],
            layout: 'horizontal',
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 19. matcher
  {
    _id: 'demo-matcher',
    widgetTypes: ['matcher'],
    question: {
      content: 'Match each word with its definition:\n\n[[☃ matcher 1]]',
      widgets: {
        'matcher 1': {
          type: 'matcher',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            left: ['Benevolent', 'Ephemeral', 'Ubiquitous'],
            right: ['Kind and generous', 'Short-lived', 'Present everywhere'],
            labels: ['Word', 'Definition'],
            orderMatters: false,
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 20. orderer
  {
    _id: 'demo-orderer',
    widgetTypes: ['orderer'],
    question: {
      content: 'Arrange these historical events in chronological order:\n\n[[☃ orderer 1]]',
      widgets: {
        'orderer 1': {
          type: 'orderer',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            correctOptions: [
              { content: 'American Revolution (1776)' },
              { content: 'French Revolution (1789)' },
              { content: 'War of 1812 (1812)' },
              { content: 'Civil War (1861)' },
            ],
            layout: 'vertical',
            otherOptions: [],
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 21. label-image
  {
    _id: 'demo-label-image',
    widgetTypes: ['label-image'],
    question: {
      content: 'Label the parts of the cell:\n\n[[☃ label-image 1]]',
      widgets: {
        'label-image 1': {
          type: 'label-image',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            imageUrl: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 300 200'%3E%3Cellipse cx='150' cy='100' rx='130' ry='80' fill='%23fef3c7' stroke='%23f59e0b' stroke-width='3'/%3E%3Ccircle cx='150' cy='100' r='30' fill='%23818cf8' stroke='%234f46e5' stroke-width='2'/%3E%3Ccircle cx='150' cy='100' r='10' fill='%231e1b4b'/%3E%3C/svg%3E",
            imageAlt: 'Diagram of a cell',
            imageWidth: 300,
            imageHeight: 200,
            choices: ['Nucleus', 'Cell Membrane', 'Cytoplasm'],
            markers: [
              { x: 150, y: 100, label: '' },
              { x: 30, y: 100, label: '' },
            ],
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 22. matrix
  {
    _id: 'demo-matrix',
    widgetTypes: ['matrix'],
    question: {
      content: 'Enter the 2x2 identity matrix:\n\n[[☃ matrix 1]]',
      widgets: {
        'matrix 1': {
          type: 'matrix',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            matrixBoardSize: [2, 2],
            answers: [['1', '0'], ['0', '1']],
            prefix: '',
            suffix: '',
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 23. free-response
  {
    _id: 'demo-free-response',
    widgetTypes: ['free-response'],
    question: {
      content: 'Explain why photosynthesis is important for life on Earth.\n\n[[☃ free-response 1]]',
      widgets: {
        'free-response 1': {
          type: 'free-response',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            placeholder: 'Type your response here...',
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 24. cs-program
  {
    _id: 'demo-cs-program',
    widgetTypes: ['cs-program'],
    question: {
      content: 'What is the output of this Python code?\n\n[[☃ cs-program 1]]',
      widgets: {
        'cs-program 1': {
          type: 'cs-program',
          alignment: 'default',
          static: true,
          graded: false,
          options: {
            programID: 'demo-python',
            height: 200,
            settings: [{ name: 'code', value: 'for i in range(3):\n    print(f"Hello {i}")' }],
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 25. measurer
  {
    _id: 'demo-measurer',
    widgetTypes: ['measurer'],
    question: {
      content: 'Use the ruler to measure the length of the line:\n\n[[☃ measurer 1]]',
      widgets: {
        'measurer 1': {
          type: 'measurer',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            rulerLength: 10,
            rulerPixels: 400,
            rulerTicks: 10,
            rulerLabel: 'cm',
            box: [400, 200],
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 26. molecule
  {
    _id: 'demo-molecule',
    widgetTypes: ['molecule'],
    question: {
      content: 'The molecule below is **water (H₂O)**:\n\n[[☃ molecule 1]]',
      widgets: {
        'molecule 1': {
          type: 'molecule',
          alignment: 'default',
          static: true,
          graded: false,
          options: {
            smiles: 'O',
            rotationAngle: 0,
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 27. iframe
  {
    _id: 'demo-iframe',
    widgetTypes: ['iframe'],
    question: {
      content: 'Interact with the simulation below:\n\n[[☃ iframe 1]]',
      widgets: {
        'iframe 1': {
          type: 'iframe',
          alignment: 'default',
          static: true,
          graded: false,
          options: {
            url: 'https://phet.colorado.edu/sims/html/balancing-act/latest/balancing-act_en.html',
            width: 500,
            height: 350,
            allowFullscreen: true,
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 28. group
  {
    _id: 'demo-group',
    widgetTypes: ['group'],
    question: {
      content: 'Solve both parts:\n\n[[☃ group 1]]',
      widgets: {
        'group 1': {
          type: 'group',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            content: 'Part A: What is 2 + 2?\n\n[[☃ numeric-input 1]]\n\nPart B: What is 3 + 3?\n\n[[☃ numeric-input 2]]',
            widgets: {
              'numeric-input 1': {
                type: 'numeric-input',
                options: { answers: [{ value: 4, status: 'correct' }], size: 'small' },
              },
              'numeric-input 2': {
                type: 'numeric-input',
                options: { answers: [{ value: 6, status: 'correct' }], size: 'small' },
              },
            },
            images: {},
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 29. graded-group
  {
    _id: 'demo-graded-group',
    widgetTypes: ['graded-group'],
    question: {
      content: 'Complete all parts for full credit:\n\n[[☃ graded-group 1]]',
      widgets: {
        'graded-group 1': {
          type: 'graded-group',
          alignment: 'default',
          static: false,
          graded: true,
          options: {
            title: 'Problem Set A',
            content: 'Solve: 5 × 5 = [[☃ numeric-input 1]]',
            widgets: {
              'numeric-input 1': {
                type: 'numeric-input',
                options: { answers: [{ value: 25, status: 'correct' }], size: 'small' },
              },
            },
            images: {},
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },

  // 30. passage-ref
  {
    _id: 'demo-passage-ref',
    widgetTypes: ['passage-ref'],
    question: {
      content: 'What does the author mean by "self-evident" in [[☃ passage-ref 1]]?',
      widgets: {
        'passage-ref 1': {
          type: 'passage-ref',
          alignment: 'inline',
          static: true,
          graded: false,
          options: {
            passageNumber: 1,
            referenceNumber: 1,
            summaryText: 'line 1',
          },
          version: { major: 0, minor: 0 },
        },
      },
      images: {},
    },
    hints: [],
    answerArea: {},
  },
];
