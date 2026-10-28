# CP08 abrupt runner loss with surviving supervisor

The existing real-container hosted step now runs a second bounded case after SIGTERM passes. It starts an owned runner in a supervisor-owned temporary namespace, waits for a running real restricted container, verifies its unique name and source mount, then sends SIGKILL only to that runner PID.

The supervisor must observe the runner's -SIGKILL return, a still-running orphan and existing staging. It explicitly removes that exact container and owned staging, independently verifies absence and confirms no runner final report exists. Cleanup fallback cannot convert failed primary checks into success.

This establishes only controlled runner-process loss and foreground surviving-supervisor cleanup. It does not install a supervisor, recover after host loss, prove GitHub cancellation behavior, establish deletion of provider replicas or automatic retention expiry. CP08 remains partial; score stays 11/19.

Local full suite: 216 distinct tests passed. Docker unavailable locally; hosted evidence pending at publication. No workflow/trigger/credential/provider-data change. Owner standing nonbilling approval applies to continuing this bounded sandbox test and reviewable repository change; production remains paused.
