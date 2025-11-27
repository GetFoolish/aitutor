# Knowledge Graph (Curriculum Structure Only)- Developer Brief

This is the map of how concepts connect. It's the same for every student.

**Important:** This is ONLY for curriculum structure. We do NOT track student mastery or struggles here - that's what the DASH system handles.

**What the Knowledge Graph stores:**
- Topic relationships (prerequisites, dependencies)
- Concept hierarchies (what's part of what)

**What it does NOT store:**
- Student mastery (DASH handles this)
- Student struggles (DASH handles this)
- Practice history (DASH handles this)
- Memory strength (DASH handles this)

### How It Gets Built

The knowledge graph is **generated automatically** from curriculum content. You don't manually define relationships - the system figures them out.

**Input (what you can upload in each run):**
- Questions (JSONs)
- AND/OR Curriculum content:
  - Text (textbook chapters, notes)
  - Images (diagrams, charts)
  - Videos (lectures)
  - Audio (explanations)

**Process:**
1. LLM analyzes all input content
2. Extracts concepts and their relationships
3. Determines prerequisites based on content structure
4. Merges with existing knowledge graph (or creates new if first run)

**Output:**
- Enriched question JSONs (with `requires`, `part_of` fields added)
- Updated knowledge graph file

### The Flow

```
┌─────────────────────┐
│ Input:              │
│ - Questions (JSONs) │
│ - Curriculum (text, │
│   images, video,    │
│   audio)            │
│ - Previous KG       │
│   (or null/empty)   │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ LLM Analysis:       │
│ - Extract concepts  │
│ - Determine prereqs │
│ - Find relationships│
│ - Merge with        │
│   existing KG       │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Output:             │
│ - Enriched Q JSONs  │
│   (with requires,   │
│    part_of fields)  │
│ - Updated KG file   │
└─────────────────────┘
```

### Question JSON Before/After

**Before (raw question):**
```json
{
  "id": "q_123",
  "question": "Find the discriminant of x² + 5x + 6",
  "topic": "quadratics"
}
```

**After (enriched with relationships):**
```json
{
  "id": "q_123",
  "question": "Find the discriminant of x² + 5x + 6",
  "topic": "quadratics",
  "concept": "discriminant",
  "requires": ["quadratic_formula", "basic_algebra"],
  "part_of": "quadratics"
}
```

### Incremental Building

The knowledge graph grows with your curriculum:

1. **First run:** Empty KG + initial questions/content → KG v1
2. **Add content:** KG v1 + new questions/videos → KG v2
3. **Keep adding:** KG v2 + more content → KG v3

You can start with nothing and build it up over time. Each ingestion run takes the previous graph and extends it.

### Example: What the graph looks like

```
(Quadratics) --[REQUIRES]--> (Factoring)
(Discriminant) --[PART_OF]--> (Quadratics)
(Completing_Square) --[PART_OF]--> (Quadratics)
(Factoring) --[REQUIRES]--> (Basic_Algebra)
```

No student-specific edges. The graph is static curriculum data.

### How to use it with DASH

When deciding what to teach next:
1. Query DASH: "What skills does Alex have weak memory strength on?"
2. Query Knowledge Graph: "What are the prerequisites for those weak skills?"
3. Cross-reference: "Are any prerequisites also weak in DASH?"
4. Decision: "Strengthen prerequisites first"

The knowledge graph provides the **structure**. DASH provides the **student state**. They complement each other.

**Tech choice:** Neo4j is the standard, but you could start simpler with a JSON structure. The key is that relationships are explicit and traversable.

**Priority:** This can be built after the vector DB personalization is working. But it's essential for intelligent curriculum sequencing.

---

### How to Demo (Knowledge Graph Builder)

Use the question bank to demonstrate the knowledge graph being built and enriched.

**Input:** `SherlockEDApi/CurriculumBuilder/` (5000+ questions in Perseus JSON format)

Each question file contains:
```json
{
  "question": {
    "content": "**Which place value model shows $2{,}923$?**\n\n[[☃ radio 1]]",
    "widgets": { ... }
  },
  "hints": [ ... ],
  "answerArea": { ... }
}
```

**The Builder:**

```python
class KnowledgeGraphBuilder:
    """
    Processes question JSONs and curriculum content to build/extend
    the knowledge graph with verbose logging.
    """

    def __init__(self, verbose=True):
        self.verbose = verbose
        self.graph = {}  # Or Neo4j connection
        self.concepts = set()
        self.relationships = []
        self.stats = {
            "questions_processed": 0,
            "concepts_extracted": 0,
            "relationships_created": 0
        }

    def process_question_bank(self, questions_dir, existing_graph=None):
        """Process all questions in directory"""
        if existing_graph:
            self.graph = self.load_graph(existing_graph)
            self.log(f"[INIT] Loaded existing graph: {len(self.graph['concepts'])} concepts, {len(self.graph['relationships'])} relationships")
        else:
            self.log(f"[INIT] Starting with empty graph")

        # Get all question files
        question_files = list(glob(f"{questions_dir}/*.json"))
        total = len(question_files)
        self.log(f"[START] Processing {total} questions from {questions_dir}")

        # Process in batches for efficiency
        batch_size = 100
        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch_files = question_files[batch_start:batch_end]

            self.log(f"\n[BATCH] Processing questions {batch_start+1}-{batch_end}/{total}")

            # Extract concepts from batch
            batch_concepts = []
            batch_relationships = []

            for qfile in batch_files:
                result = self.process_question(qfile)
                if result:
                    batch_concepts.extend(result['concepts'])
                    batch_relationships.extend(result['relationships'])
                    self.stats['questions_processed'] += 1

            # Log batch results
            new_concepts = [c for c in batch_concepts if c not in self.concepts]
            self.log(f"[BATCH] New concepts: {len(new_concepts)}")
            self.log(f"[BATCH] New relationships: {len(batch_relationships)}")

            if new_concepts:
                self.log(f"[BATCH] Concepts: {', '.join(new_concepts[:10])}{'...' if len(new_concepts) > 10 else ''}")

            # Merge into graph
            self.concepts.update(batch_concepts)
            self.relationships.extend(batch_relationships)
            self.stats['concepts_extracted'] = len(self.concepts)
            self.stats['relationships_created'] = len(self.relationships)

        # Final validation
        self.validate_graph()

        return self.get_results()

    def process_question(self, question_file):
        """Extract concepts and relationships from a single question"""
        question_data = load_json(question_file)

        # Extract question text from Perseus format
        question_text = question_data.get('question', {}).get('content', '')
        hints = question_data.get('hints', [])

        # LLM call to extract concepts and prerequisites
        extraction_prompt = f"""Analyze this question and extract:
1. The main concept being tested
2. Prerequisites needed to answer it
3. What broader topic it's part of

Question: {question_text}
Hints: {[h.get('content', '') for h in hints[:2]]}

Return JSON:
{{
  "concept": "the main concept",
  "requires": ["prerequisite1", "prerequisite2"],
  "part_of": "broader topic"
}}
"""
        result = llm_call(extraction_prompt)

        if result:
            # Build enriched question
            enriched = {
                **question_data,
                "concept": result['concept'],
                "requires": result['requires'],
                "part_of": result['part_of']
            }

            # Save enriched question
            self.save_enriched_question(question_file, enriched)

            return {
                'concepts': [result['concept']] + result['requires'] + [result['part_of']],
                'relationships': [
                    {'from': result['concept'], 'to': req, 'type': 'REQUIRES'}
                    for req in result['requires']
                ] + [
                    {'from': result['concept'], 'to': result['part_of'], 'type': 'PART_OF'}
                ]
            }

        return None

    def validate_graph(self):
        """Run validation checks on the built graph"""
        self.log(f"\n{'='*50}")
        self.log(f"[VALIDATION] Running graph validation...")

        # Check for orphans
        orphans = self.find_orphan_concepts()
        self.log(f"[VALIDATION] Orphan concepts: {len(orphans)}")
        if orphans:
            self.log(f"  Warning: {', '.join(orphans[:5])}{'...' if len(orphans) > 5 else ''}")

        # Check for circular dependencies
        cycles = self.find_cycles()
        self.log(f"[VALIDATION] Circular dependencies: {len(cycles)}")
        if cycles:
            self.log(f"  Warning: {cycles[:3]}")

        # Check prerequisite depth
        max_depth = self.get_max_prerequisite_depth()
        self.log(f"[VALIDATION] Max prerequisite depth: {max_depth}")

        # Sample prerequisite chains
        self.log(f"\n[VALIDATION] Sample prerequisite chains:")
        chains = self.get_sample_chains(3)
        for chain in chains:
            self.log(f"  {' → '.join(chain)}")

    def get_results(self):
        """Return final results with summary"""
        self.log(f"\n{'='*50}")
        self.log(f"[COMPLETE] Knowledge Graph Built")
        self.log(f"[STATS] Questions processed: {self.stats['questions_processed']}")
        self.log(f"[STATS] Total concepts: {self.stats['concepts_extracted']}")
        self.log(f"[STATS] Total relationships: {self.stats['relationships_created']}")

        return {
            'concepts': list(self.concepts),
            'relationships': self.relationships,
            'stats': self.stats
        }

    def log(self, message):
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] {message}")


# Run the demo
if __name__ == "__main__":
    builder = KnowledgeGraphBuilder(verbose=True)

    results = builder.process_question_bank(
        questions_dir="SherlockEDApi/CurriculumBuilder",
        existing_graph=None  # Or path to previous graph
    )

    # Save final graph
    save_json("knowledge_graph.json", results)
```

**Expected Output (Dev Mode):**

```
[09:00:01.100] [INIT] Starting with empty graph
[09:00:01.102] [START] Processing 5000 questions from SherlockEDApi/CurriculumBuilder

[BATCH] Processing questions 1-100/5000
[09:00:05.234] [BATCH] New concepts: 47
[09:00:05.235] [BATCH] New relationships: 89
[09:00:05.236] [BATCH] Concepts: place_value, thousands, hundreds, tens, ones, number_representation, addition, subtraction, comparison, ordering...

[BATCH] Processing questions 101-200/5000
[09:00:09.567] [BATCH] New concepts: 38
[09:00:09.568] [BATCH] New relationships: 72
[09:00:09.569] [BATCH] Concepts: multiplication, division, arrays, equal_groups, skip_counting, repeated_addition...

[BATCH] Processing questions 201-300/5000
[09:00:13.891] [BATCH] New concepts: 41
[09:00:13.892] [BATCH] New relationships: 85
[09:00:13.893] [BATCH] Concepts: fractions, numerator, denominator, equivalent_fractions, comparing_fractions, mixed_numbers...

...

[BATCH] Processing questions 4901-5000/5000
[09:08:45.123] [BATCH] New concepts: 12
[09:08:45.124] [BATCH] New relationships: 34
[09:08:45.125] [BATCH] Concepts: quadratic_formula, discriminant, completing_square... (merged with existing)

==================================================
[09:08:46.000] [VALIDATION] Running graph validation...
[09:08:46.234] [VALIDATION] Orphan concepts: 0
[09:08:46.456] [VALIDATION] Circular dependencies: 0
[09:08:46.678] [VALIDATION] Max prerequisite depth: 8

[09:08:46.700] [VALIDATION] Sample prerequisite chains:
  discriminant → quadratic_formula → factoring → basic_algebra
  completing_square → perfect_squares → multiplication → addition
  systems_of_equations → linear_equations → variables → basic_algebra

==================================================
[09:08:47.000] [COMPLETE] Knowledge Graph Built
[09:08:47.001] [STATS] Questions processed: 5000
[09:08:47.002] [STATS] Total concepts: 847
[09:08:47.003] [STATS] Total relationships: 2341

[09:08:47.100] Sample enriched questions:

BEFORE: {"question": {"content": "Find the discriminant of x² + 5x + 6"}}
AFTER:  {
  "question": {"content": "Find the discriminant of x² + 5x + 6"},
  "concept": "discriminant",
  "requires": ["quadratic_formula", "basic_algebra"],
  "part_of": "quadratics"
}

BEFORE: {"question": {"content": "Which place value model shows 2,923?"}}
AFTER:  {
  "question": {"content": "Which place value model shows 2,923?"},
  "concept": "place_value_models",
  "requires": ["place_value", "thousands", "hundreds", "tens", "ones"],
  "part_of": "number_representation"
}
```

**What this demonstrates:**
- Batch processing of 5000 questions
- Concepts being extracted and merged
- Prerequisites determined automatically
- Enriched question JSONs with `requires`, `part_of`, `concept` fields
- Validation ensuring graph integrity
- Sample prerequisite chains showing curriculum structure

**Running incrementally:**
```python
# First run - build initial graph
builder.process_question_bank("SherlockEDApi/CurriculumBuilder/batch1")

# Later - extend with more content
builder.process_question_bank(
    "SherlockEDApi/CurriculumBuilder/batch2",
    existing_graph="knowledge_graph_v1.json"
)
```

---
