# minitalk Project Guide

## Project Overview

This is the 42 school "minitalk" project: a client-server communication program that exclusively uses UNIX signals (SIGUSR1 and SIGUSR2) for inter-process communication.

## Core Requirements

### Mandatory Part
1. **Server** - starts first, prints its PID on launch
2. **Client** - takes two parameters:
   - Server PID
   - String to send
3. **Communication** - exclusively via SIGUSR1 and SIGUSR2
4. **Performance** - must display 100 characters within 1 second (critical constraint)
5. **Robustness** - server must handle multiple clients sequentially without restart

### Key Technical Constraints
- **Signal queuing limitation**: Linux does NOT queue signals when you already have pending signals of the same type. This is a fundamental challenge to solve.
- **Only two signals allowed**: SIGUSR1 and SIGUSR2 (must encode data with these)
- **No delays**: Visible lag during display is unacceptable

### Bonus Features (only if mandatory is perfect)
1. Server acknowledges each received message by sending signal back to client
2. Unicode character support

## README Requirements
Must include:
- First line: italicized attribution line with login(s)
- Description section (project goal and brief overview)
- Instructions section (compilation, installation, execution)
- Resources section (references + explanation of AI usage)
- Additional sections as needed (usage examples, technical choices, etc.)

## Success Criteria

✅ **Mandatory Complete** = perfect implementation of all mandatory features
✅ **Performance** = 100 chars displays in <1 second
✅ **README** = complete with all required sections
✅ **Code Quality** = clean, efficient signal handling

## How I Can Help

- Design the signal encoding scheme for data transmission
- Implement efficient server/client signal handlers
- Optimize for performance and handle the signal queuing limitation
- Debug timing/performance issues
- Write/refine the README with proper formatting
- Test with various input sizes and edge cases
- Add bonus features once mandatory part is solid

## Key Implementation Notes

- Think carefully about how to encode multiple bits of information using only 2 signals
- Signal handlers should be minimal and fast
- Consider how to handle the lack of signal queuing
- Server state management for handling multiple clients

## Build verification

- Run `make` to ensure that the project compiles

## Evaluation

### Prerequisites (Must Pass)
- Non-empty submission with correct files
- No Norm errors
- No compilation errors or Makefile that re-links
- Code must not contain evidence of cheating

### General Instructions (5 points available)
- **Makefile compiles both executables** → 1 point
- **Server named 'server' displays its PID at launch** → 2 points
- **Client named 'client' launches as: `/client PID_SERVER STRING_TO_PASS`** → 2 points

### Mandatory Part (5+ points available)

#### Message Transmission
- Messages of any size can be transmitted
- Messages received are displayed correctly by server
- Server never remains blocked or displays incorrect characters
- **Rate: 0 (failed) through 5 (excellent)**

#### Simple Configuration (4 points available)
- **Server can receive multiple strings without restart** → 1 point
- **At most one global variable per program, or none** → 1 point
- **Communication uses ONLY signals SIGUSR1 and SIGUSR2** → 3 points
- **Rate: 0 (failed) through 5 (excellent)**

### Bonus Part (only if mandatory is excellent)

Bonuses are ONLY examined if the mandatory part is complete and perfect.

#### Unicode Character Support
- Both client and server support Unicode characters
- **Points: Pass/Fail**

#### Message Acknowledgment
- Server confirms receipt of each message by sending a signal to client
- **Points: Pass/Fail**