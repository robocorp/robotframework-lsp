import { window, ProgressLocation, Progress } from 'vscode';


class ProgressReporter {

    promise: Thenable<Progress<{ message?: string; increment?: number }>>;
    resolve;
    progress: Progress<{ message?: string; increment?: number }>;

    start(args: ProgressReport) {
        window.withProgress(
            { location: ProgressLocation.Notification, title: args.title, cancellable: false }, p => {
                this.progress = p;
                this.promise = new Promise((resolve, reject) => {
                    this.resolve = resolve;
                });
                return this.promise;
            });
    }

    report(args: ProgressReport) {
        if (this.progress) {
            this.progress.report(args);
        }
    }

    end() {
        if (this.resolve) {
            this.resolve();
            this.resolve = undefined;
            this.promise = undefined;
            this.progress = undefined;
        }
    }
}

let id_to_progress: Map<number, ProgressReporter> = new Map();

export interface ProgressReport {
    kind: string; // 'begin' | 'end' | 'report'
    id: number; // the id of the progress
    title?: string; // the title of the progress
    message?: string; // Only used for the 'report': The message for the progress.
    increment?: number; // Only used for the 'report': How much to increment it (0-100). Summed to previous inrcements.
}

export function handleProgressMessage(args: ProgressReport) {
    switch (args.kind) {
        case 'begin':
            let reporter: ProgressReporter = new ProgressReporter();
            reporter.start(args);
            id_to_progress[args.id] = reporter;
            break;

        case 'report':
            let prev:ProgressReporter = id_to_progress[args.id];
            if (prev) {
                prev.report(args);
            }
            break;

        case 'end':
            let last:ProgressReporter = id_to_progress[args.id];
            if (last) {
                last.end();
                id_to_progress.delete(args.id);
            }
            break;
    }
}