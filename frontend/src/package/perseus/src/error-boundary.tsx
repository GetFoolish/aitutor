import {Errors} from "@khanacademy/perseus-core";
import * as React from "react";

import {Log} from "./logging/log";

type Props = {
    children: React.ReactNode;
    metadata?: Record<string, string>;

    // A callback that is called when the error boundary traps an error.
    onError?: (error: Error, info: any) => void;
};
type State = {
    error: string;
};

class ErrorBoundary extends React.Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = {error: ""};
    }

    componentDidCatch(error: Error, info: any) {
        this.setState({error: error.toString()});
        this.props.onError?.(error, info);
        if (typeof window !== "undefined") {
            window.dispatchEvent(
                new CustomEvent("perseus-widget-render-error", {
                    detail: {
                        error: error.message,
                        metadata: this.props.metadata || {},
                    },
                }),
            );
        }
        Log.error(
            // NOTE(jeremy): We concatenate the error messsage here. Typical
            // Khan Academy error handling guidance says that you should never
            // "build" the error message that might be sent to our error
            // reporting tool (currently Sentry). However, if we don't
            // differentiate between the different errors that are thrown, they
            // all end up being grouped as a single Sentry event, which is very
            // unhelpful.
            "Unhandled Perseus error: " + error.message,
            Errors.Internal,
            {
                cause: error,
                loggedMetadata: {
                    componentStack:
                        !!info && "componentStack" in info
                            ? info.componentStack
                            : "componentStack not provided",
                    ...this.props.metadata,
                },
            },
        );
    }

    render(): React.ReactNode {
        if (this.state.error) {
            // TODO(djf): perhaps we should have one error boundary for
            // inline elements and one for block elements. This one uses
            // a <span> and effectively converts block elements with
            // errors into inline elements.
            // TODO(michaelpolyak): Link error icon to "Report a problem".
            return (
                <span
                    style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        fontSize: "12px",
                        fontWeight: 700,
                        color: "#d92916",
                    }}
                >
                    Rendering error
                </span>
            );
        }
        return this.props.children;
    }
}

export default ErrorBoundary;
