/**
 * Athena Widgets Module
 *
 * Widget components and utilities for the Athena renderer.
 */

// Registry and Factory
export { WidgetRegistry, registerDefaultWidgets } from './WidgetRegistry';
export type { WidgetComponent, WidgetProps, WidgetDefinition } from './WidgetRegistry';

export { WidgetFactory, WidgetList, useWidget } from './WidgetFactory';
export type { WidgetFactoryProps } from './WidgetFactory';

// Base components
export { BaseWidgetWrapper, useWidgetState, useWidgetId, useWidgetAria, createWidget } from './base/BaseWidget';
export type { BaseWidgetWrapperProps, UseWidgetStateOptions } from './base/BaseWidget';

// Input widgets
export { NumericInputWidget } from './input/NumericInputWidget';
export { RadioWidget } from './input/RadioWidget';
export { ExpressionWidget } from './input/ExpressionWidget';
export { DropdownWidget } from './input/DropdownWidget';

// Display widgets
export { ImageWidget } from './display/ImageWidget';
export { PassageWidget } from './display/PassageWidget';
