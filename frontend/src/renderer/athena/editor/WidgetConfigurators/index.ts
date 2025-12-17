/**
 * Widget Configurators
 *
 * Configuration UIs for all widget types.
 */

import type React from 'react';
import { NumericInputConfigurator } from './NumericInputConfigurator';
import { RadioConfigurator } from './RadioConfigurator';
import { ExpressionConfigurator } from './ExpressionConfigurator';

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
} from './BaseConfigurator';
export type { ConfiguratorProps, ConfiguratorFieldProps } from './BaseConfigurator';

export { NumericInputConfigurator } from './NumericInputConfigurator';
export { RadioConfigurator } from './RadioConfigurator';
export { ExpressionConfigurator } from './ExpressionConfigurator';

// Map widget types to their configurators
export const WIDGET_CONFIGURATORS: Record<string, React.ComponentType<any>> = {
  'numeric-input': NumericInputConfigurator,
  'input-number': NumericInputConfigurator,
  'radio': RadioConfigurator,
  'expression': ExpressionConfigurator,
};

/**
 * Get configurator for a widget type
 */
export function getWidgetConfigurator(widgetType: string): React.ComponentType<any> | null {
  return WIDGET_CONFIGURATORS[widgetType] || null;
}
