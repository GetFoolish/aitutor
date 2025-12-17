/**
 * Editor Frame
 *
 * Main editor shell for creating and editing Athena content.
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import type { AthenaItem, AthenaWidget, AthenaHint } from '../core/types';

export interface EditorTab {
  id: string;
  label: string;
  icon?: string;
}

export interface EditorFrameProps {
  /** Initial item to edit */
  initialItem?: AthenaItem;
  /** Called when content changes */
  onChange?: (item: AthenaItem) => void;
  /** Called on save */
  onSave?: (item: AthenaItem) => void;
  /** Custom tabs to display */
  tabs?: EditorTab[];
  /** Default active tab */
  defaultTab?: string;
  /** Whether to show JSON pane */
  showJSON?: boolean;
  /** Whether to show preview pane */
  showPreview?: boolean;
  /** Editor height */
  height?: string | number;
  /** Custom class name */
  className?: string;
  /** Render custom toolbar content */
  renderToolbar?: (item: AthenaItem) => React.ReactNode;
  /** Children for additional panes */
  children?: React.ReactNode;
}

export interface EditorFrameRef {
  /** Get current item */
  getItem: () => AthenaItem;
  /** Set item */
  setItem: (item: AthenaItem) => void;
  /** Get specific widget */
  getWidget: (widgetId: string) => AthenaWidget | undefined;
  /** Update widget */
  updateWidget: (widgetId: string, widget: AthenaWidget) => void;
  /** Add widget */
  addWidget: (widget: AthenaWidget) => string;
  /** Remove widget */
  removeWidget: (widgetId: string) => void;
  /** Undo last change */
  undo: () => boolean;
  /** Redo last undone change */
  redo: () => boolean;
  /** Check if can undo */
  canUndo: () => boolean;
  /** Check if can redo */
  canRedo: () => boolean;
}

interface HistoryEntry {
  item: AthenaItem;
  timestamp: number;
}

const DEFAULT_ITEM: AthenaItem = {
  question: {
    content: '',
    widgets: {},
    images: {},
  },
  hints: [],
  answerArea: {
    type: 'single',
    widgets: {},
  },
  itemDataVersion: { major: 0, minor: 0 },
};

const DEFAULT_TABS: EditorTab[] = [
  { id: 'content', label: 'Content', icon: 'edit' },
  { id: 'widgets', label: 'Widgets', icon: 'cube' },
  { id: 'hints', label: 'Hints', icon: 'lightbulb' },
  { id: 'settings', label: 'Settings', icon: 'cog' },
];

/**
 * Main editor frame component
 */
export const EditorFrame = React.forwardRef<EditorFrameRef, EditorFrameProps>(
  function EditorFrame(
    {
      initialItem,
      onChange,
      onSave,
      tabs = DEFAULT_TABS,
      defaultTab = 'content',
      showJSON = true,
      showPreview = true,
      height = '600px',
      className = '',
      renderToolbar,
      children,
    },
    ref
  ) {
    const [item, setItemState] = useState<AthenaItem>(initialItem || DEFAULT_ITEM);
    const [activeTab, setActiveTab] = useState(defaultTab);
    const [showJSONPane, setShowJSONPane] = useState(false);
    const [showPreviewPane, setShowPreviewPane] = useState(showPreview);
    const [isDirty, setIsDirty] = useState(false);

    // History for undo/redo
    const historyRef = useRef<HistoryEntry[]>([{ item: initialItem || DEFAULT_ITEM, timestamp: Date.now() }]);
    const historyIndexRef = useRef(0);
    const isUpdatingRef = useRef(false);

    // Generate unique widget ID
    const generateWidgetId = useCallback((type: string): string => {
      const existingIds = Object.keys(item.question.widgets);
      let counter = 1;
      let id = `${type} ${counter}`;
      while (existingIds.includes(id)) {
        counter++;
        id = `${type} ${counter}`;
      }
      return id;
    }, [item.question.widgets]);

    // Update item with history tracking
    const updateItem = useCallback((newItem: AthenaItem, addToHistory = true) => {
      if (addToHistory && !isUpdatingRef.current) {
        // Truncate history if we're not at the end
        if (historyIndexRef.current < historyRef.current.length - 1) {
          historyRef.current = historyRef.current.slice(0, historyIndexRef.current + 1);
        }
        // Add new entry
        historyRef.current.push({ item: newItem, timestamp: Date.now() });
        historyIndexRef.current = historyRef.current.length - 1;

        // Limit history size
        if (historyRef.current.length > 50) {
          historyRef.current.shift();
          historyIndexRef.current--;
        }
      }

      setItemState(newItem);
      setIsDirty(true);
      onChange?.(newItem);
    }, [onChange]);

    // Undo
    const undo = useCallback((): boolean => {
      if (historyIndexRef.current > 0) {
        isUpdatingRef.current = true;
        historyIndexRef.current--;
        const entry = historyRef.current[historyIndexRef.current];
        setItemState(entry.item);
        onChange?.(entry.item);
        isUpdatingRef.current = false;
        return true;
      }
      return false;
    }, [onChange]);

    // Redo
    const redo = useCallback((): boolean => {
      if (historyIndexRef.current < historyRef.current.length - 1) {
        isUpdatingRef.current = true;
        historyIndexRef.current++;
        const entry = historyRef.current[historyIndexRef.current];
        setItemState(entry.item);
        onChange?.(entry.item);
        isUpdatingRef.current = false;
        return true;
      }
      return false;
    }, [onChange]);

    // Expose ref methods
    React.useImperativeHandle(ref, () => ({
      getItem: () => item,
      setItem: (newItem: AthenaItem) => updateItem(newItem),
      getWidget: (widgetId: string) => item.question.widgets[widgetId],
      updateWidget: (widgetId: string, widget: AthenaWidget) => {
        updateItem({
          ...item,
          question: {
            ...item.question,
            widgets: {
              ...item.question.widgets,
              [widgetId]: widget,
            },
          },
        });
      },
      addWidget: (widget: AthenaWidget) => {
        const id = generateWidgetId(widget.type);
        updateItem({
          ...item,
          question: {
            ...item.question,
            widgets: {
              ...item.question.widgets,
              [id]: widget,
            },
          },
        });
        return id;
      },
      removeWidget: (widgetId: string) => {
        const { [widgetId]: removed, ...remainingWidgets } = item.question.widgets;
        // Also remove placeholder from content
        const content = item.question.content.replace(
          new RegExp(`\\[\\[☃\\s*${widgetId}\\s*\\]\\]`, 'g'),
          ''
        );
        updateItem({
          ...item,
          question: {
            ...item.question,
            content,
            widgets: remainingWidgets,
          },
        });
      },
      undo,
      redo,
      canUndo: () => historyIndexRef.current > 0,
      canRedo: () => historyIndexRef.current < historyRef.current.length - 1,
    }), [item, updateItem, generateWidgetId, undo, redo]);

    // Handle save
    const handleSave = useCallback(() => {
      onSave?.(item);
      setIsDirty(false);
    }, [item, onSave]);

    // Handle keyboard shortcuts
    useEffect(() => {
      const handleKeyDown = (e: KeyboardEvent) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
          e.preventDefault();
          handleSave();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
          e.preventDefault();
          if (e.shiftKey) {
            redo();
          } else {
            undo();
          }
        }
        if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
          e.preventDefault();
          redo();
        }
      };

      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }, [handleSave, undo, redo]);

    // Update content
    const handleContentChange = useCallback((content: string) => {
      updateItem({
        ...item,
        question: {
          ...item.question,
          content,
        },
      });
    }, [item, updateItem]);

    // Update hints
    const handleHintsChange = useCallback((hints: AthenaHint[]) => {
      updateItem({
        ...item,
        hints,
      });
    }, [item, updateItem]);

    const containerStyle: React.CSSProperties = {
      height: typeof height === 'number' ? `${height}px` : height,
    };

    return (
      <div className={`athena-editor-frame ${className}`} style={containerStyle}>
        {/* Toolbar */}
        <div className="athena-editor-toolbar">
          <div className="athena-editor-toolbar-left">
            {/* Tab buttons */}
            <div className="athena-editor-tabs" role="tablist">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  role="tab"
                  aria-selected={activeTab === tab.id}
                  className={`athena-editor-tab ${activeTab === tab.id ? 'athena-editor-tab--active' : ''}`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  {tab.icon && <span className={`athena-icon athena-icon--${tab.icon}`} />}
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          <div className="athena-editor-toolbar-center">
            {renderToolbar?.(item)}
          </div>

          <div className="athena-editor-toolbar-right">
            {/* Undo/Redo */}
            <button
              className="athena-editor-btn"
              onClick={undo}
              disabled={historyIndexRef.current === 0}
              title="Undo (Ctrl+Z)"
              aria-label="Undo"
            >
              <span className="athena-icon athena-icon--undo" />
            </button>
            <button
              className="athena-editor-btn"
              onClick={redo}
              disabled={historyIndexRef.current >= historyRef.current.length - 1}
              title="Redo (Ctrl+Y)"
              aria-label="Redo"
            >
              <span className="athena-icon athena-icon--redo" />
            </button>

            <div className="athena-editor-divider" />

            {/* View toggles */}
            {showJSON && (
              <button
                className={`athena-editor-btn ${showJSONPane ? 'athena-editor-btn--active' : ''}`}
                onClick={() => setShowJSONPane(!showJSONPane)}
                title="Toggle JSON view"
                aria-pressed={showJSONPane}
              >
                <span className="athena-icon athena-icon--code" />
                JSON
              </button>
            )}
            {showPreview && (
              <button
                className={`athena-editor-btn ${showPreviewPane ? 'athena-editor-btn--active' : ''}`}
                onClick={() => setShowPreviewPane(!showPreviewPane)}
                title="Toggle preview"
                aria-pressed={showPreviewPane}
              >
                <span className="athena-icon athena-icon--eye" />
                Preview
              </button>
            )}

            <div className="athena-editor-divider" />

            {/* Save button */}
            <button
              className={`athena-editor-btn athena-editor-btn--primary ${isDirty ? 'athena-editor-btn--dirty' : ''}`}
              onClick={handleSave}
              title="Save (Ctrl+S)"
            >
              <span className="athena-icon athena-icon--save" />
              Save
              {isDirty && <span className="athena-editor-dirty-indicator" />}
            </button>
          </div>
        </div>

        {/* Main content area */}
        <div className="athena-editor-content">
          {/* Editor panels */}
          <div className={`athena-editor-panels ${showPreviewPane ? 'athena-editor-panels--with-preview' : ''}`}>
            {/* Main editor panel */}
            <div className="athena-editor-main" role="tabpanel" aria-labelledby={`tab-${activeTab}`}>
              <EditorContext.Provider value={{
                item,
                updateItem,
                activeTab,
                generateWidgetId,
                onContentChange: handleContentChange,
                onHintsChange: handleHintsChange,
              }}>
                {children}
              </EditorContext.Provider>
            </div>

            {/* Preview panel */}
            {showPreviewPane && (
              <div className="athena-editor-preview">
                <div className="athena-editor-preview-header">
                  <span>Preview</span>
                  <button
                    className="athena-editor-btn athena-editor-btn--small"
                    onClick={() => setShowPreviewPane(false)}
                    aria-label="Close preview"
                  >
                    <span className="athena-icon athena-icon--close" />
                  </button>
                </div>
                <div className="athena-editor-preview-content">
                  {/* Preview content rendered by child components */}
                </div>
              </div>
            )}
          </div>

          {/* JSON panel (drawer) */}
          {showJSONPane && (
            <div className="athena-editor-json-drawer">
              <div className="athena-editor-json-header">
                <span>JSON</span>
                <div className="athena-editor-json-actions">
                  <button
                    className="athena-editor-btn athena-editor-btn--small"
                    onClick={() => {
                      navigator.clipboard.writeText(JSON.stringify(item, null, 2));
                    }}
                    title="Copy JSON"
                  >
                    <span className="athena-icon athena-icon--copy" />
                  </button>
                  <button
                    className="athena-editor-btn athena-editor-btn--small"
                    onClick={() => setShowJSONPane(false)}
                    aria-label="Close JSON view"
                  >
                    <span className="athena-icon athena-icon--close" />
                  </button>
                </div>
              </div>
              <pre className="athena-editor-json-content">
                {JSON.stringify(item, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Status bar */}
        <div className="athena-editor-statusbar">
          <span className="athena-editor-status-item">
            {Object.keys(item.question.widgets).length} widgets
          </span>
          <span className="athena-editor-status-item">
            {item.hints.length} hints
          </span>
          {isDirty && (
            <span className="athena-editor-status-item athena-editor-status-item--dirty">
              Unsaved changes
            </span>
          )}
        </div>
      </div>
    );
  }
);

// Editor context for child components
export interface EditorContextValue {
  item: AthenaItem;
  updateItem: (item: AthenaItem) => void;
  activeTab: string;
  generateWidgetId: (type: string) => string;
  onContentChange: (content: string) => void;
  onHintsChange: (hints: AthenaHint[]) => void;
}

export const EditorContext = React.createContext<EditorContextValue | null>(null);

export function useEditorContext(): EditorContextValue {
  const context = React.useContext(EditorContext);
  if (!context) {
    throw new Error('useEditorContext must be used within an EditorFrame');
  }
  return context;
}

export default EditorFrame;
