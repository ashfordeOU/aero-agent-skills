# cFS Architecture Reference Notes

External facts about NASA core Flight Software (cFS) used by this leaf.
Facts here are reference material, not reproduced standard text; cFS is
open source (Apache-2.0) at github.com/nasa/cFS. Verify against the
current cFS release before freezing a design.

## Layering

| Layer | Responsibility | Examples |
|---|---|---|
| PSP | Board-specific: CPU reset, clock, memory, EEPROM, console | pc-rtems, pc-linux PSPs |
| OSAL | RTOS abstraction: tasks, semaphores, queues, timers, filesystem, network | OS_TaskCreate, OS_QueuePut |
| cFE core | Reusable services, platform independent | ES, SB, EVS, TBL, TIME, FS |
| Flight apps | Mission software on top of the cFE APIs | GNC, ACS, EPS, FDIR apps |

One PSP per target processor; one OSAL port per RTOS (RTEMS, VxWorks,
POSIX); the cFE core and apps are RTOS and processor independent.

## cFE core services

- Executive Services (ES): app registration and startup/shutdown,
  memory pool management, reset control, housekeeping catalog.
- Software Bus (SB): message routing by message ID; apps subscribe and
  publish; SB copies each message to every subscriber's pipe.
- Event Services (EVS): severity-filtered event messages for operator
  and FDIR visibility; runtime filtering per app.
- Table Services (TBL): loadable configuration tables with validation,
  update, and dump.
- Time Services (TIME): time source management, time sync messages,
  spacecraft time.
- File Services (FS): filesystem utilities, file headers, file/disk
  housekeeping helpers.

## Message ID layout (classic cFE 6.x)

- Message IDs are 16-bit (CFE_SB_MsgId_t).
- Command traffic occupies 0x0000-0x0FFF; telemetry 0x1000-0xFFFF.
- Classic packing: upper bits carry the app tag, lower bits the message
  number within the app. Example: 0x1900 = app 0x19, message 0x00.
- Modern cFE (6.7+) widened CFE_SB_MsgId_t to 32 bits; apps now get an
  application ID and message IDs are derived from it. The 16-bit model
  remains the documented classic layout and the model this leaf simulates.

## App lifecycle

- Canonical pattern: APP_Main calls APP_Init once, then loops calling
  APP_Execute.
- APP_Init: one-time startup, register with ES, subscribe to command
  message IDs, load tables.
- APP_Execute: per-cycle body, route pending SB messages, run cycle
  work.
- APP_Data: process one received message or produce the cycle's
  telemetry.

## Telemetry header

- CFE_SB_TlmHdr carries a sequence counter (SeqCnt) that increments per
  message, letting ground stations detect dropped packets.
- The simulation mirrors this with monotonic per-message-ID counters in
  telemetry_pipeline().

## Event severity levels (CFE_EVS)

- DEBUG, INFO, EVENT, ERROR, CRITICAL.
- Typical use: DEBUG for diagnostics, INFO/EVENT for normal milestones,
  ERROR for recoverable faults, CRITICAL for loss of function.

## Version notes

- cFS was open-sourced by NASA in 2015; cFE 6.x is the long-standing
  classic line. The current cFS bundle (cfe 6.8+, osal 5.x) uses
  message-ID refactors and updated APIs.
- Licensing: Apache-2.0 for the cFS bundle, matching this leaf.
