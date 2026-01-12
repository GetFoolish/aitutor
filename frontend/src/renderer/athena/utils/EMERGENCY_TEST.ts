// EMERGENCY SIMPLE VERSION - Just to test if rendering works at all
export const processContent_SIMPLE = (content: string): string => {
    if (!content) return '';

    try {
        // Just return the content with widget placeholders converted
        let processed = content;

        // Convert widget placeholders to spans
        processed = processed.replace(/\[\[☃\s+([^\]]+)\]\]/g, (_, widgetId) => {
            return `<span class="athena-widget-inline" data-widget-id="${widgetId.trim()}"></span>`;
        });

        return processed;
    } catch (error) {
        console.error('[Athena] CRASH:', error);
        return `<div>ERROR: ${error.message}</div>`;
    }
};
