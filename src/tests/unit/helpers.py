from dataclasses import dataclass


@dataclass
class FakeResponse:
    content: str


class FakeLlm:
    def __init__(self, content: str):
        self.content = content
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        return FakeResponse(self.content)


class FakeExecutor:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def invoke(self, payload):
        self.calls.append(payload)
        return self.result