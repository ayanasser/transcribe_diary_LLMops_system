"""
Tests for the telemetry module
"""
import unittest
from unittest.mock import patch, MagicMock

from shared.utils.telemetry import setup_telemetry, get_tracer, create_span, extract_context_from_headers


class TestTelemetry(unittest.TestCase):
    """Test cases for OpenTelemetry integration"""
    
    @patch('shared.utils.telemetry.trace')
    @patch('shared.utils.telemetry.BatchSpanProcessor')
    @patch('shared.utils.telemetry.OTLPSpanExporter')
    def test_setup_telemetry_with_otlp(self, mock_exporter, mock_processor, mock_trace):
        """Test telemetry setup with OTLP enabled"""
        mock_settings = MagicMock()
        mock_settings.observability.otlp_endpoint = "http://collector:4317"
        mock_settings.observability.otlp_insecure = True
        mock_settings.environment = "test"
        
        with patch('shared.utils.telemetry.settings', mock_settings):
            tracer = setup_telemetry("test-service")
            
            # Verify trace provider was set up
            mock_trace.set_tracer_provider.assert_called_once()
            mock_exporter.assert_called_once_with(
                endpoint="http://collector:4317",
                insecure=True
            )
            mock_processor.assert_called_once()
            mock_trace.get_tracer_provider.return_value.add_span_processor.assert_called_once()
            mock_trace.get_tracer.assert_called_once_with("test-service")
    
    @patch('shared.utils.telemetry.trace')
    def test_setup_telemetry_without_otlp(self, mock_trace):
        """Test telemetry setup without OTLP endpoint"""
        mock_settings = MagicMock()
        mock_settings.observability.otlp_endpoint = None
        
        with patch('shared.utils.telemetry.settings', mock_settings):
            tracer = setup_telemetry("test-service")
            
            # Verify default tracer was set up
            mock_trace.set_tracer_provider.assert_called_once()
            mock_trace.get_tracer.assert_called_once_with("test-service")
    
    @patch('shared.utils.telemetry.get_tracer')
    def test_create_span(self, mock_get_tracer):
        """Test span creation"""
        mock_tracer = MagicMock()
        mock_get_tracer.return_value = mock_tracer
        
        span = create_span("test-span", {"key": "value"})
        
        mock_get_tracer.assert_called_once()
        mock_tracer.start_span.assert_called_once_with("test-span")
        mock_tracer.start_span.return_value.set_attribute.assert_called_once_with("key", "value")
    
    @patch('shared.utils.telemetry.TraceContextTextMapPropagator')
    def test_extract_context(self, mock_propagator):
        """Test extracting context from headers"""
        mock_instance = MagicMock()
        mock_propagator.return_value = mock_instance
        
        headers = {"traceparent": "00-0af7651916cd43dd8448eb211c80319c-b9c7c989f97918e1-01"}
        context = extract_context_from_headers(headers)
        
        mock_instance.extract.assert_called_once_with(headers)


if __name__ == '__main__':
    unittest.main()
