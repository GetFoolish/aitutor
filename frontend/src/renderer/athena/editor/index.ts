/**
 * Athena Editor Module
 *
 * Content authoring and editing system.
 */

// Main editor components
export { EditorFrame, useEditorContext, EditorContext } from './EditorFrame';
export type { EditorFrameProps, EditorFrameRef, EditorTab, EditorContextValue } from './EditorFrame';

export { ContentEditor } from './ContentEditor';
export type { ContentEditorProps, ContentEditorRef } from './ContentEditor';

export { PreviewPane } from './PreviewPane';
export type { PreviewPaneProps } from './PreviewPane';

export { JSONPane } from './JSONPane';
export type { JSONPaneProps } from './JSONPane';

export { WidgetInserter } from './WidgetInserter';
export type { WidgetInserterProps, WidgetTemplate } from './WidgetInserter';

export { HintEditor } from './HintEditor';
export type { HintEditorProps } from './HintEditor';

// Widget configurators
export {
  BaseConfigurator,
  ConfiguratorField,
  ConfiguratorSection,
  ConfiguratorInput,
  ConfiguratorTextarea,
  ConfiguratorCheckbox,
  ConfiguratorSelect,
  ConfiguratorNumber,
  ConfiguratorArray,
  NumericInputConfigurator,
  RadioConfigurator,
  ExpressionConfigurator,
  getWidgetConfigurator,
  WIDGET_CONFIGURATORS,
} from './WidgetConfigurators';
export type { ConfiguratorProps, ConfiguratorFieldProps } from './WidgetConfigurators';
