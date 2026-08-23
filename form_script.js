// Paste this into:
// Helpdesk Admin → HD Form Script → New
// DocType: HD Ticket
// Script: (this entire file contents below)

const actions = [
  {
    label: "Analyze Traceback",
    onClick: () => {
      createToast({ title: "Analyzing traceback...", variant: "info" });

      call(
        "helpdesk_ai.api.analyze.run",
        { ticket_name: doc.name },
        (result) => {
          if (!result.found) {
            createToast({
              title: "No traceback found",
              message: "No Python traceback detected in this ticket.",
              variant: "warning",
            });
            return;
          }

          const partialNote = result.partial
            ? '<p style="color:#b45309;font-size:0.85em;margin-top:8px">⚠ Only exception line found — analysis may be incomplete.</p>'
            : "";

          const unknownNote = !result.known
            ? '<p style="color:#6b7280;font-size:0.85em;margin-top:8px">Exception not in known patterns — showing general guidance.</p>'
            : "";

          const html = `
            <div>
              <p style="color:#6b7280;font-size:0.85em;margin-bottom:8px">
                Exception: <code>${result.exception_class}</code>
              </p>
              <h4 style="margin-bottom:4px">Root Cause</h4>
              <p>${result.root_cause}</p>
              <h4 style="margin-bottom:4px;margin-top:12px">How to Fix</h4>
              <p style="white-space:pre-line">${result.fix}</p>
              ${partialNote}
              ${unknownNote}
            </div>`;

          $dialog({
            title: "Traceback Analysis",
            message: html,
            size: "large",
            primaryAction: {
              label: "Copy Fix",
              onClick: () => {
                navigator.clipboard.writeText(result.fix).then(() => {
                  createToast({ title: "Copied!", variant: "success" });
                });
              },
            },
          });
        }
      );
    },
  },
];
