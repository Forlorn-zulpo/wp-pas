class AIClientError(Exception):
    pass


class AICompletionResult:
    def __init__(self, text: str, input_tokens: int, output_tokens: int, duration_ms: int):
        self.text = text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.duration_ms = duration_ms
