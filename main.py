import sys
import time


class Node:
    def __init__(self, value, next_node=None):
        self.value = value
        self.next = next_node


class Stack:
    def __init__(self):
        self.top_node = None

    def push(self, value):
        self.top_node = Node(value, self.top_node)

    def pop(self):
        if self.top_node is None:
            return None

        value = self.top_node.value
        self.top_node = self.top_node.next
        return value

    def top(self):
        if self.top_node is None:
            return None

        return self.top_node.value

    def is_empty(self):
        return self.top_node is None


def is_valid_name(name):
    return bool(name) and name.isalnum()


def read_events(input_file):
    events = []

    with open(
        input_file,
        "r",
        encoding="utf-8",
        errors="replace"
    ) as file:
        for line_number, line in enumerate(file, 1):
            parts = line.split()

            if parts:
                events.append((line_number, parts))

    return events


def detect_format(events):
    for _, parts in events:
        if len(parts) not in (2, 3):
            continue

        if parts[0] not in ("LOGIN", "LOGOUT"):
            continue

        if not is_valid_name(parts[1]):
            continue

        return len(parts)

    return 2


def parse_event(parts, event_format):
    if len(parts) != event_format:
        return None

    action = parts[0]
    name = parts[1]

    if action not in ("LOGIN", "LOGOUT"):
        return None

    if not is_valid_name(name):
        return None

    timestamp = None

    if event_format == 3:
        try:
            timestamp = int(parts[2])
        except ValueError:
            return None

        if timestamp < 0:
            return None

    return action, name, timestamp


def process_events(events, event_format):
    stacks = {}
    errors = []

    sessions_count = 0
    active_sessions = 0

    peak_concurrent = 0
    peak_line = 0

    previous_timestamp = None
    total_duration = 0
    completed_with_time = 0

    for line_number, parts in events:
        event = parse_event(parts, event_format)

        if event is None:
            errors.append((line_number, "bad_event"))
            continue

        action, name, timestamp = event

        if event_format == 3:
            if (
                previous_timestamp is not None
                and timestamp < previous_timestamp
            ):
                errors.append((line_number, "bad_event"))
                continue

            previous_timestamp = timestamp

        if action == "LOGIN":
            stack = stacks.get(name)

            if stack is None:
                stack = Stack()
                stacks[name] = stack

            stack.push((line_number, timestamp))
            active_sessions += 1

            if active_sessions > peak_concurrent:
                peak_concurrent = active_sessions
                peak_line = line_number

        else:
            stack = stacks.get(name)

            if stack is None or stack.is_empty():
                errors.append(
                    (line_number, "logout_without_login")
                )
                continue

            login_line, login_time = stack.pop()

            sessions_count += 1
            active_sessions -= 1

            if event_format == 3:
                total_duration += timestamp - login_time
                completed_with_time += 1

            if stack.is_empty():
                del stacks[name]

    unclosed_errors = []

    for stack in stacks.values():
        while not stack.is_empty():
            login_line, _ = stack.pop()
            unclosed_errors.append(
                (login_line, "session_not_closed")
            )

    unclosed_errors.sort()
    errors.extend(unclosed_errors)

    average_duration = None

    if event_format == 3:
        if completed_with_time > 0:
            average_duration = (
                total_duration / completed_with_time
            )
        else:
            average_duration = 0.0

    return (
        errors,
        sessions_count,
        peak_concurrent,
        peak_line,
        average_duration
    )


def write_result(output_file, errors, sessions_count):
    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:
        for line_number, error in errors:
            file.write(
                f"ERROR {line_number} {error}\n"
            )

        file.write(
            f"SESSIONS {sessions_count}\n"
        )


def process_log(input_file, output_file):
    events = read_events(input_file)

    event_format = detect_format(events)

    result = process_events(
        events,
        event_format
    )

    (
        errors,
        sessions_count,
        peak_concurrent,
        peak_line,
        average_duration
    ) = result

    write_result(
        output_file,
        errors,
        sessions_count
    )

    print(
        f"# stats: peak_concurrent={peak_concurrent} "
        f"at line={peak_line}",
        file=sys.stderr
    )

    if average_duration is not None:
        print(
            f"# stats: avg_duration={average_duration:.3f}",
            file=sys.stderr
        )


def benchmark(input_file):
    start = time.perf_counter()

    events = read_events(input_file)

    read_time = time.perf_counter() - start

    event_format = detect_format(events)

    start = time.perf_counter()

    process_events(
        events,
        event_format
    )

    parse_time = time.perf_counter() - start

    print(
        f"# benchmark: read={read_time:.6f}s "
        f"parse={parse_time:.6f}s",
        file=sys.stderr
    )


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--benchmark":
        try:
            benchmark(sys.argv[2])
        except (FileNotFoundError, OSError) as error:
            print(
                f"Input error: {error}",
                file=sys.stderr
            )
            sys.exit(1)

        return

    if len(sys.argv) == 3:
        try:
            process_log(
                sys.argv[1],
                sys.argv[2]
            )
        except (FileNotFoundError, OSError) as error:
            print(
                f"Input error: {error}",
                file=sys.stderr
            )
            sys.exit(1)

        return

    if len(sys.argv) == 2 and sys.argv[1] == "--help":
        print(
            "Usage: python main.py input.txt output.txt"
        )
        print(
            "       python main.py --benchmark input.txt"
        )
        return

    print(
        "Usage: python main.py input.txt output.txt"
    )
    sys.exit(1)


if __name__ == "__main__":
    main()