"""Tests for LLM response parser."""

from unittest.mock import Mock

from app.llm.response_parser import LLMResponseParser
from app.models.llm import LLMResponse


class TestLLMResponseParser:
    """Test LLM response parser."""

    def test_parse_openai_response(self):
        """Test parsing OpenAI response."""
        # Mock OpenAI response structure
        mock_response = Mock()
        mock_response.model = "gpt-3.5-turbo"
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Hello, world!"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5

        response = LLMResponseParser.parse_openai_response(mock_response)

        assert isinstance(response, LLMResponse)
        assert response.content == "Hello, world!"
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 5
        assert response.model == "gpt-3.5-turbo"
        assert response.total_tokens == 15

    def test_parse_openai_response_empty_content(self):
        """Test parsing OpenAI response with None content."""
        mock_response = Mock()
        mock_response.model = "gpt-4"
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = None
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 0

        response = LLMResponseParser.parse_openai_response(mock_response)

        assert response.content == ""
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 0

    def test_parse_openai_response_no_choices(self):
        """Test parsing OpenAI response with no choices."""
        mock_response = Mock()
        mock_response.model = "gpt-4"
        mock_response.choices = []
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 0

        response = LLMResponseParser.parse_openai_response(mock_response)

        assert response.content == ""

    def test_parse_openai_response_no_usage(self):
        """Test parsing OpenAI response with no usage data."""
        mock_response = Mock()
        mock_response.model = "gpt-4"
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Test"
        mock_response.usage = None

        response = LLMResponseParser.parse_openai_response(mock_response)

        assert response.prompt_tokens == 0
        assert response.completion_tokens == 0
        assert response.total_tokens == 0

    def test_parse_anthropic_response(self):
        """Test parsing Anthropic response."""
        # Mock Anthropic response structure
        mock_response = Mock()
        mock_response.model = "claude-3-sonnet-20240229"
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Hello from Claude!"
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 15
        mock_response.usage.output_tokens = 8

        response = LLMResponseParser.parse_anthropic_response(mock_response)

        assert isinstance(response, LLMResponse)
        assert response.content == "Hello from Claude!"
        assert response.prompt_tokens == 15
        assert response.completion_tokens == 8
        assert response.model == "claude-3-sonnet-20240229"
        assert response.total_tokens == 23

    def test_parse_anthropic_response_empty_content(self):
        """Test parsing Anthropic response with empty content."""
        mock_response = Mock()
        mock_response.model = "claude-3-opus"
        mock_response.content = []
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 0

        response = LLMResponseParser.parse_anthropic_response(mock_response)

        assert response.content == ""
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 0

    def test_parse_anthropic_response_multiple_content_blocks(self):
        """Test parsing Anthropic response uses first content block."""
        mock_response = Mock()
        mock_response.model = "claude-3-sonnet"
        mock_response.content = [Mock(), Mock()]
        mock_response.content[0].text = "First block"
        mock_response.content[1].text = "Second block"
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5

        response = LLMResponseParser.parse_anthropic_response(mock_response)

        # Should use first content block
        assert response.content == "First block"

    def test_extract_openai_content(self):
        """Test extracting content from OpenAI response."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Test content"

        content = LLMResponseParser._extract_openai_content(mock_response)

        assert content == "Test content"

    def test_extract_openai_content_handles_none(self):
        """Test extracting None content returns empty string."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = None

        content = LLMResponseParser._extract_openai_content(mock_response)

        assert content == ""

    def test_extract_openai_usage(self):
        """Test extracting usage from OpenAI response."""
        mock_response = Mock()
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 20
        mock_response.usage.completion_tokens = 30

        usage = LLMResponseParser._extract_openai_usage(mock_response)

        assert usage["prompt_tokens"] == 20
        assert usage["completion_tokens"] == 30

    def test_extract_openai_usage_handles_none(self):
        """Test extracting None usage returns zeros."""
        mock_response = Mock()
        mock_response.usage = None

        usage = LLMResponseParser._extract_openai_usage(mock_response)

        assert usage["prompt_tokens"] == 0
        assert usage["completion_tokens"] == 0

    def test_extract_anthropic_content(self):
        """Test extracting content from Anthropic response."""
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Claude's response"

        content = LLMResponseParser._extract_anthropic_content(mock_response)

        assert content == "Claude's response"

    def test_extract_anthropic_content_handles_empty(self):
        """Test extracting empty content returns empty string."""
        mock_response = Mock()
        mock_response.content = []

        content = LLMResponseParser._extract_anthropic_content(mock_response)

        assert content == ""

    def test_extract_anthropic_usage(self):
        """Test extracting usage from Anthropic response."""
        mock_response = Mock()
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 25
        mock_response.usage.output_tokens = 35

        usage = LLMResponseParser._extract_anthropic_usage(mock_response)

        assert usage["prompt_tokens"] == 25
        assert usage["completion_tokens"] == 35

    def test_create_empty_response(self):
        """Test creating empty response."""
        response = LLMResponseParser.create_empty_response()

        assert response.content == ""
        assert response.prompt_tokens == 0
        assert response.completion_tokens == 0
        assert response.model == "unknown"
        assert response.total_tokens == 0

    def test_create_empty_response_with_model(self):
        """Test creating empty response with custom model."""
        response = LLMResponseParser.create_empty_response(model="gpt-4")

        assert response.content == ""
        assert response.model == "gpt-4"
        assert response.total_tokens == 0
