/**
 * Placeholder Widgets for Specialized Types
 *
 * These are placeholder implementations for specialized widgets
 * that require external libraries (VexFlow, Leaflet, etc.).
 * They show a meaningful preview with the widget configuration.
 */

import React from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import { BaseWidgetWrapper } from '../base/BaseWidget';

// ============================================================================
// MOLECULE WIDGET
// ============================================================================

interface MoleculeOptions {
  smiles: string;
  rotationAngle?: number;
}

export function MoleculeWidget({
  widgetId,
  widget,
  theme = 'light',
}: WidgetProps<MoleculeOptions>) {
  const options = widget.options || {};

  const themeStyles = {
    light: { bg: '#fce7f3', border: '#ec4899', text: '#9d174d' },
    dark: { bg: '#4a0e2e', border: '#ec4899', text: '#fbcfe8' },
    'high-contrast': { bg: '#000', border: '#f0f', text: '#f0f' },
  }[theme];

  // Simple molecule representation for common SMILES
  const moleculeNames: Record<string, string> = {
    'O': 'H₂O (Water)',
    'CC': 'C₂H₆ (Ethane)',
    'C': 'CH₄ (Methane)',
    'CCO': 'C₂H₅OH (Ethanol)',
    'C=O': 'CO₂ (Carbon Dioxide)',
    'N': 'NH₃ (Ammonia)',
  };

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="molecule">
      <div
        style={{
          padding: '24px',
          backgroundColor: themeStyles.bg,
          border: `2px solid ${themeStyles.border}`,
          borderRadius: '12px',
          textAlign: 'center',
        }}
      >
        <div style={{ fontSize: '48px', marginBottom: '12px' }}>⚗️</div>
        <div style={{ fontWeight: 600, color: themeStyles.text, fontSize: '18px' }}>
          {options.smiles ? (moleculeNames[options.smiles] || `Molecule: ${options.smiles}`) : 'Molecule Structure'}
        </div>
        <div style={{ color: themeStyles.text, opacity: 0.7, fontSize: '14px', marginTop: '8px' }}>
          SMILES: {options.smiles || 'N/A'}
        </div>
      </div>
    </BaseWidgetWrapper>
  );
}

// ============================================================================
// REACTION DIAGRAM WIDGET
// ============================================================================

interface ReactionDiagramOptions {
  reactants?: string[];
  products?: string[];
  equation?: string;
}

export function ReactionDiagramWidget({
  widgetId,
  widget,
  theme = 'light',
}: WidgetProps<ReactionDiagramOptions>) {
  const options = widget.options || {};

  const themeStyles = {
    light: { bg: '#fce7f3', border: '#ec4899', text: '#9d174d' },
    dark: { bg: '#4a0e2e', border: '#ec4899', text: '#fbcfe8' },
    'high-contrast': { bg: '#000', border: '#f0f', text: '#f0f' },
  }[theme];

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="reaction-diagram">
      <div
        style={{
          padding: '24px',
          backgroundColor: themeStyles.bg,
          border: `2px solid ${themeStyles.border}`,
          borderRadius: '12px',
          textAlign: 'center',
        }}
      >
        <div style={{ fontSize: '24px', fontWeight: 600, color: themeStyles.text, fontFamily: 'serif' }}>
          {options.equation || 'Chemical Reaction'}
        </div>
        {Array.isArray(options.reactants) && Array.isArray(options.products) && (
          <div style={{ marginTop: '16px', color: themeStyles.text, fontSize: '14px' }}>
            Reactants: {options.reactants.join(' + ')} → Products: {options.products.join(' + ')}
          </div>
        )}
      </div>
    </BaseWidgetWrapper>
  );
}

// ============================================================================
// MUSIC NOTATION WIDGET
// ============================================================================

interface MusicNotationOptions {
  clef?: string;
  keySignature?: string;
  timeSignature?: string;
  notes?: string[];
}

export function MusicNotationWidget({
  widgetId,
  widget,
  theme = 'light',
}: WidgetProps<MusicNotationOptions>) {
  const options = widget.options || {};

  const themeStyles = {
    light: { bg: '#fdf2f8', border: '#f472b6', text: '#9d174d' },
    dark: { bg: '#4a0e2e', border: '#f472b6', text: '#fbcfe8' },
    'high-contrast': { bg: '#000', border: '#f0f', text: '#f0f' },
  }[theme];

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="music-notation">
      <div
        style={{
          padding: '24px',
          backgroundColor: themeStyles.bg,
          border: `2px solid ${themeStyles.border}`,
          borderRadius: '12px',
          textAlign: 'center',
        }}
      >
        <div style={{ fontSize: '48px', marginBottom: '12px' }}>🎼</div>
        <div style={{ fontWeight: 600, color: themeStyles.text, fontSize: '18px' }}>
          {options.clef || 'Treble'} Clef - {options.timeSignature || '4/4'}
        </div>
        {Array.isArray(options.notes) && options.notes.length > 0 && (
          <div style={{ marginTop: '12px', color: themeStyles.text, fontSize: '16px', fontFamily: 'serif' }}>
            Notes: {options.notes.join(' - ')}
          </div>
        )}
      </div>
    </BaseWidgetWrapper>
  );
}

// ============================================================================
// CS PROGRAM WIDGET
// ============================================================================

interface CSProgramOptions {
  code: string;
  language?: string;
  showLineNumbers?: boolean;
  highlightLines?: number[];
}

export function CSProgramWidget({
  widgetId,
  widget,
  theme = 'light',
}: WidgetProps<CSProgramOptions>) {
  const options = widget.options || {};

  const themeStyles = {
    light: { bg: '#1f2937', border: '#374151', text: '#f3f4f6', lineNum: '#6b7280' },
    dark: { bg: '#111827', border: '#374151', text: '#f3f4f6', lineNum: '#4b5563' },
    'high-contrast': { bg: '#000', border: '#fff', text: '#0f0', lineNum: '#666' },
  }[theme];

  const code = options.code || '// No code provided';
  const lines = code.split('\n');

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="cs-program">
      <div
        style={{
          backgroundColor: themeStyles.bg,
          border: `1px solid ${themeStyles.border}`,
          borderRadius: '8px',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            padding: '8px 16px',
            backgroundColor: themeStyles.border,
            color: themeStyles.text,
            fontSize: '12px',
            fontWeight: 500,
          }}
        >
          {options.language || 'code'}
        </div>
        <pre
          style={{
            margin: 0,
            padding: '16px',
            color: themeStyles.text,
            fontFamily: 'monospace',
            fontSize: '14px',
            lineHeight: 1.5,
            overflow: 'auto',
          }}
        >
          {lines.map((line, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                backgroundColor: options.highlightLines?.includes(i + 1) ? 'rgba(59, 130, 246, 0.2)' : 'transparent',
              }}
            >
              {options.showLineNumbers && (
                <span style={{ color: themeStyles.lineNum, marginRight: '16px', userSelect: 'none' }}>
                  {String(i + 1).padStart(2, ' ')}
                </span>
              )}
              <code>{line}</code>
            </div>
          ))}
        </pre>
      </div>
    </BaseWidgetWrapper>
  );
}

// ============================================================================
// IFRAME WIDGET
// ============================================================================

interface IframeOptions {
  url: string;
  width?: number;
  height?: number;
  allowFullscreen?: boolean;
}

export function IframeWidget({
  widgetId,
  widget,
  theme = 'light',
}: WidgetProps<IframeOptions>) {
  const options = widget.options || {};

  const themeStyles = {
    light: { bg: '#f3f4f6', border: '#e5e7eb', text: '#374151' },
    dark: { bg: '#374151', border: '#4b5563', text: '#f3f4f6' },
    'high-contrast': { bg: '#000', border: '#fff', text: '#fff' },
  }[theme];

  const url = options.url || '';
  let hostname = 'Unknown';
  try {
    if (url) hostname = new URL(url).hostname;
  } catch {
    hostname = 'Invalid URL';
  }

  if (!url) {
    return (
      <BaseWidgetWrapper widgetId={widgetId} widgetType="iframe">
        <div style={{ padding: '24px', textAlign: 'center', color: themeStyles.text }}>
          No URL provided for iframe
        </div>
      </BaseWidgetWrapper>
    );
  }

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="iframe">
      <div
        style={{
          border: `2px solid ${themeStyles.border}`,
          borderRadius: '8px',
          overflow: 'hidden',
          backgroundColor: themeStyles.bg,
        }}
      >
        <div
          style={{
            padding: '8px 12px',
            backgroundColor: themeStyles.border,
            color: themeStyles.text,
            fontSize: '12px',
          }}
        >
          External Content: {hostname}
        </div>
        <iframe
          src={url}
          width={options.width || '100%'}
          height={options.height || 400}
          style={{ border: 'none', display: 'block' }}
          allowFullScreen={options.allowFullscreen}
          title="Embedded content"
        />
      </div>
    </BaseWidgetWrapper>
  );
}

// ============================================================================
// TIMELINE WIDGET
// ============================================================================

interface TimelineEvent {
  date: string;
  title: string;
  description?: string;
}

interface TimelineOptions {
  events: TimelineEvent[];
}

export function TimelineWidget({
  widgetId,
  widget,
  theme = 'light',
}: WidgetProps<TimelineOptions>) {
  const options = widget.options || {};

  const themeStyles = {
    light: { bg: '#fef2f2', border: '#ef4444', text: '#991b1b', line: '#fca5a5' },
    dark: { bg: '#450a0a', border: '#ef4444', text: '#fecaca', line: '#7f1d1d' },
    'high-contrast': { bg: '#000', border: '#f00', text: '#fff', line: '#f00' },
  }[theme];

  const events = Array.isArray(options.events) ? options.events : [];

  if (events.length === 0) {
    return (
      <BaseWidgetWrapper widgetId={widgetId} widgetType="timeline">
        <div style={{ padding: '24px', textAlign: 'center', color: themeStyles.text }}>
          No timeline events configured
        </div>
      </BaseWidgetWrapper>
    );
  }

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="timeline">
      <div style={{ padding: '16px' }}>
        <div
          style={{
            position: 'relative',
            paddingLeft: '24px',
            borderLeft: `3px solid ${themeStyles.line}`,
          }}
        >
          {events.map((event, i) => (
            <div
              key={i}
              style={{
                position: 'relative',
                marginBottom: '24px',
                paddingLeft: '16px',
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  left: '-30px',
                  width: '14px',
                  height: '14px',
                  backgroundColor: themeStyles.border,
                  borderRadius: '50%',
                }}
              />
              <div
                style={{
                  padding: '12px 16px',
                  backgroundColor: themeStyles.bg,
                  borderRadius: '8px',
                  border: `1px solid ${themeStyles.line}`,
                }}
              >
                <div style={{ fontWeight: 600, color: themeStyles.border, fontSize: '14px' }}>
                  {event.date}
                </div>
                <div style={{ fontWeight: 600, color: themeStyles.text, marginTop: '4px' }}>
                  {event.title}
                </div>
                {event.description && (
                  <div style={{ color: themeStyles.text, opacity: 0.8, marginTop: '4px', fontSize: '14px' }}>
                    {event.description}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </BaseWidgetWrapper>
  );
}

// ============================================================================
// MAP WIDGET
// ============================================================================

interface MapMarker {
  lat: number;
  lng: number;
  label?: string;
}

interface MapOptions {
  center?: [number, number];
  zoom?: number;
  markers?: MapMarker[];
}

export function MapWidget({
  widgetId,
  widget,
  theme = 'light',
}: WidgetProps<MapOptions>) {
  const options = widget.options || {};

  const themeStyles = {
    light: { bg: '#ecfeff', border: '#06b6d4', text: '#0e7490' },
    dark: { bg: '#083344', border: '#06b6d4', text: '#a5f3fc' },
    'high-contrast': { bg: '#000', border: '#0ff', text: '#0ff' },
  }[theme];

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="map">
      <div
        style={{
          padding: '24px',
          backgroundColor: themeStyles.bg,
          border: `2px solid ${themeStyles.border}`,
          borderRadius: '12px',
          textAlign: 'center',
        }}
      >
        <div style={{ fontSize: '48px', marginBottom: '12px' }}>🗺️</div>
        <div style={{ fontWeight: 600, color: themeStyles.text, fontSize: '18px' }}>
          Interactive Map
        </div>
        {Array.isArray(options.center) && options.center.length >= 2 && (
          <div style={{ color: themeStyles.text, opacity: 0.7, fontSize: '14px', marginTop: '8px' }}>
            Center: {options.center[0].toFixed(4)}, {options.center[1].toFixed(4)}
          </div>
        )}
        {Array.isArray(options.markers) && options.markers.length > 0 && (
          <div style={{ marginTop: '16px' }}>
            {options.markers.map((marker, i) => (
              <div
                key={i}
                style={{
                  display: 'inline-block',
                  margin: '4px',
                  padding: '4px 12px',
                  backgroundColor: themeStyles.border,
                  color: 'white',
                  borderRadius: '4px',
                  fontSize: '12px',
                }}
              >
                📍 {marker.label || `(${marker.lat.toFixed(2)}, ${marker.lng.toFixed(2)})`}
              </div>
            ))}
          </div>
        )}
      </div>
    </BaseWidgetWrapper>
  );
}

// ============================================================================
// MEASURER WIDGET
// ============================================================================

interface MeasurerOptions {
  rulerLength?: number;
  rulerPixels?: number;
  rulerTicks?: number;
  rulerLabel?: string;
  box?: [number, number];
}

export function MeasurerWidget({
  widgetId,
  widget,
  theme = 'light',
}: WidgetProps<MeasurerOptions>) {
  const options = widget.options || {};

  const themeStyles = {
    light: { bg: '#f9fafb', border: '#d1d5db', text: '#374151', ruler: '#fef3c7' },
    dark: { bg: '#374151', border: '#4b5563', text: '#f3f4f6', ruler: '#78350f' },
    'high-contrast': { bg: '#000', border: '#fff', text: '#fff', ruler: '#ff0' },
  }[theme];

  const rulerLength = options.rulerLength || 10;
  const rulerLabel = options.rulerLabel || 'cm';

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="measurer">
      <div
        style={{
          padding: '24px',
          backgroundColor: themeStyles.bg,
          border: `2px solid ${themeStyles.border}`,
          borderRadius: '12px',
        }}
      >
        <div style={{ fontWeight: 600, color: themeStyles.text, marginBottom: '16px' }}>
          Measurement Tool
        </div>
        <div
          style={{
            position: 'relative',
            height: '40px',
            backgroundColor: themeStyles.ruler,
            border: `1px solid ${themeStyles.border}`,
            borderRadius: '4px',
          }}
        >
          {Array.from({ length: rulerLength + 1 }).map((_, i) => (
            <div
              key={i}
              style={{
                position: 'absolute',
                left: `${(i / rulerLength) * 100}%`,
                bottom: 0,
                width: '1px',
                height: i % 5 === 0 ? '20px' : '10px',
                backgroundColor: themeStyles.text,
              }}
            >
              {i % 5 === 0 && (
                <span
                  style={{
                    position: 'absolute',
                    bottom: '22px',
                    left: '-8px',
                    fontSize: '10px',
                    color: themeStyles.text,
                  }}
                >
                  {i}
                </span>
              )}
            </div>
          ))}
        </div>
        <div style={{ textAlign: 'center', marginTop: '8px', color: themeStyles.text, fontSize: '12px' }}>
          {rulerLength} {rulerLabel}
        </div>
      </div>
    </BaseWidgetWrapper>
  );
}

// ============================================================================
// GROUP WIDGETS
// ============================================================================

interface GroupOptions {
  content?: string;
  widgets?: Record<string, unknown>;
  images?: Record<string, unknown>;
  title?: string;
}

export function GroupWidget({
  widgetId,
  widget,
  theme = 'light',
}: WidgetProps<GroupOptions>) {
  const options = widget.options || {};

  const themeStyles = {
    light: { bg: '#f9fafb', border: '#e5e7eb', text: '#374151' },
    dark: { bg: '#374151', border: '#4b5563', text: '#f3f4f6' },
    'high-contrast': { bg: '#000', border: '#fff', text: '#fff' },
  }[theme];

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="group">
      <div
        style={{
          padding: '16px',
          backgroundColor: themeStyles.bg,
          border: `1px solid ${themeStyles.border}`,
          borderRadius: '8px',
        }}
      >
        {options.title && (
          <div style={{ fontWeight: 600, color: themeStyles.text, marginBottom: '12px' }}>
            {options.title}
          </div>
        )}
        <div style={{ color: themeStyles.text, whiteSpace: 'pre-wrap' }}>
          {options.content || '[Widget Group]'}
        </div>
      </div>
    </BaseWidgetWrapper>
  );
}

interface GradedGroupOptions {
  title?: string;
  content?: string;
  widgets?: Record<string, unknown>;
  images?: Record<string, unknown>;
}

export function GradedGroupWidget({
  widgetId,
  widget,
  theme = 'light',
}: WidgetProps<GradedGroupOptions>) {
  const options = widget.options || {};

  const themeStyles = {
    light: { bg: '#eff6ff', border: '#3b82f6', text: '#1e40af' },
    dark: { bg: '#1e3a5f', border: '#60a5fa', text: '#93c5fd' },
    'high-contrast': { bg: '#000', border: '#00f', text: '#00f' },
  }[theme];

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="graded-group">
      <div
        style={{
          padding: '16px',
          backgroundColor: themeStyles.bg,
          border: `2px solid ${themeStyles.border}`,
          borderRadius: '8px',
        }}
      >
        {options.title && (
          <div style={{ fontWeight: 600, color: themeStyles.text, marginBottom: '12px' }}>
            {options.title}
          </div>
        )}
        <div style={{ color: themeStyles.text, whiteSpace: 'pre-wrap' }}>
          {options.content || '[Graded Group]'}
        </div>
      </div>
    </BaseWidgetWrapper>
  );
}

interface GradedGroupSetOptions {
  gradedGroups?: Array<{ title?: string; content?: string; widgets?: Record<string, unknown> }>;
}

export function GradedGroupSetWidget({
  widgetId,
  widget,
  theme = 'light',
}: WidgetProps<GradedGroupSetOptions>) {
  const options = widget.options || {};

  const themeStyles = {
    light: { bg: '#f9fafb', border: '#6b7280', text: '#374151' },
    dark: { bg: '#374151', border: '#9ca3af', text: '#f3f4f6' },
    'high-contrast': { bg: '#000', border: '#fff', text: '#fff' },
  }[theme];

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="graded-group-set">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {options.gradedGroups?.map((group, i) => (
          <div
            key={i}
            style={{
              padding: '16px',
              backgroundColor: themeStyles.bg,
              border: `1px solid ${themeStyles.border}`,
              borderRadius: '8px',
            }}
          >
            {group.title && (
              <div style={{ fontWeight: 600, color: themeStyles.text, marginBottom: '8px' }}>
                {group.title}
              </div>
            )}
            <div style={{ color: themeStyles.text }}>
              {group.content || `[Group ${i + 1}]`}
            </div>
          </div>
        ))}
      </div>
    </BaseWidgetWrapper>
  );
}

// ============================================================================
// PASSAGE REF TARGET WIDGET
// ============================================================================

interface PassageRefTargetOptions {
  content?: string;
}

export function PassageRefTargetWidget({
  widgetId,
  widget,
  theme = 'light',
}: WidgetProps<PassageRefTargetOptions>) {
  const options = widget.options || {};

  const themeStyles = {
    light: { bg: '#fef9c3', text: '#854d0e' },
    dark: { bg: '#713f12', text: '#fef9c3' },
    'high-contrast': { bg: '#ff0', text: '#000' },
  }[theme];

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="passage-ref-target">
      <span
        style={{
          display: 'inline',
          padding: '2px 4px',
          backgroundColor: themeStyles.bg,
          color: themeStyles.text,
          borderRadius: '2px',
        }}
      >
        {options.content || '[Reference Target]'}
      </span>
    </BaseWidgetWrapper>
  );
}

export default {
  MoleculeWidget,
  ReactionDiagramWidget,
  MusicNotationWidget,
  CSProgramWidget,
  IframeWidget,
  TimelineWidget,
  MapWidget,
  MeasurerWidget,
  GroupWidget,
  GradedGroupWidget,
  GradedGroupSetWidget,
  PassageRefTargetWidget,
};
