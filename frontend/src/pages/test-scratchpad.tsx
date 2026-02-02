/**
 * Quick test page for ScratchpadTeacher
 * Access at http://localhost:3000/test-scratchpad
 */
import React, { useState } from 'react';
import { ScratchpadTeacher } from '@/components/scratchpad';

export default function TestScratchpadPage() {
  const [concept, setConcept] = useState('7 × 6');
  const [gradeLevel, setGradeLevel] = useState('3-5');
  const [key, setKey] = useState(0);

  return (
    <div className="min-h-screen bg-[#FFFDF5] p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-4">ScratchpadTeacher Test</h1>
        
        {/* Controls */}
        <div className="mb-6 p-4 bg-white border-2 border-black rounded-lg">
          <div className="flex gap-4 items-end">
            <div>
              <label className="block text-sm font-bold mb-2">Concept:</label>
              <input
                type="text"
                value={concept}
                onChange={(e) => setConcept(e.target.value)}
                className="px-3 py-2 border-2 border-black rounded"
                placeholder="e.g., 7 × 6"
              />
            </div>
            <div>
              <label className="block text-sm font-bold mb-2">Grade Level:</label>
              <select
                value={gradeLevel}
                onChange={(e) => setGradeLevel(e.target.value)}
                className="px-3 py-2 border-2 border-black rounded"
              >
                <option value="K-2">K-2</option>
                <option value="3-5">3-5</option>
                <option value="6-8">6-8</option>
                <option value="9-12">9-12</option>
              </select>
            </div>
            <button
              onClick={() => setKey(k => k + 1)}
              className="px-4 py-2 bg-[#FFD93D] border-2 border-black rounded font-bold hover:bg-[#ffd11a]"
            >
              Reload
            </button>
          </div>
        </div>

        {/* Component */}
        <ScratchpadTeacher 
          key={key}
          concept={concept}
          gradeLevel={gradeLevel}
          onComplete={() => console.log('✅ Animation complete!')}
          onPlay={() => console.log('▶️  Playing')}
          onPause={() => console.log('⏸️  Paused')}
          onStep={(step, index) => console.log(`Step ${index}:`, step.action)}
        />

        {/* Instructions */}
        <div className="mt-8 p-4 bg-white border-2 border-black rounded-lg">
          <h2 className="font-bold mb-2">Test Instructions:</h2>
          <ul className="list-disc list-inside space-y-1 text-sm">
            <li>Change concept and grade level above</li>
            <li>Click "Reload" to fetch new instructions</li>
            <li>Play/Pause/Restart controls</li>
            <li>Try different speeds: 0.5x → 2x</li>
            <li>Check browser console for step logs</li>
            <li>Backend API: POST /api/scratchpad/generate</li>
          </ul>
        </div>

        {/* Example concepts to try */}
        <div className="mt-4 p-4 bg-white border-2 border-black rounded-lg">
          <h3 className="font-bold mb-2">Example Concepts to Try:</h3>
          <div className="flex flex-wrap gap-2">
            {['2+2', '7×6', 'fractions 1/4', 'place value', '3-1'].map(c => (
              <button
                key={c}
                onClick={() => { setConcept(c); setKey(k => k + 1); }}
                className="px-3 py-1 bg-gray-100 border border-black rounded text-sm hover:bg-gray-200"
              >
                {c}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
