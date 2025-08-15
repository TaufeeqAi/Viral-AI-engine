import 'dart:convert';
import 'package:cyrene_ui/config/app_config.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/io.dart';

class WebSocketService {
  WebSocketChannel? _channel;
  final String _token;
  Function(Map<String, dynamic>)? onMessageReceived;
  Function(String)? onError;
  Function()? onConnected;
  Function()? onDisconnected;

  WebSocketService(this._token);

  Future<void> connect() async {
    print('DEBUG: WebSocketService - Attempting to connect...');
    try {
      // Ensure the token is passed as a query parameter for FastAPI WebSocket authentication
      // This is how your FastAPI server expects it based on previous interactions.
      final wsUrl = '${AppConfig.fastApiWsUrl}?token=$_token';
      print('DEBUG: WebSocketService - Connecting to URI: $wsUrl');

      _channel = IOWebSocketChannel.connect(
        Uri.parse(wsUrl),
        // Headers are typically not used for initial WebSocket auth with FastAPI's Depends(Query)
        // If your FastAPI setup uses headers for WS auth, you'd add them here.
        // headers: {'Authorization': 'Bearer $_token'},
      );

      _channel!.stream.listen(
        (data) {
          print('DEBUG: WebSocketService - Received raw data: $data');
          try {
            final message = jsonDecode(data);
            print(
              'DEBUG: WebSocketService - Received and parsed message: $message',
            );
            onMessageReceived?.call(message);
          } catch (e) {
            print(
              'ERROR: WebSocketService - Failed to parse message: $e, raw data: $data',
            );
            onError?.call('Failed to parse message: $e');
          }
        },
        onError: (error) {
          print('ERROR: WebSocketService - WebSocket stream error: $error');
          onError?.call('WebSocket stream error: $error');
        },
        onDone: () {
          print('DEBUG: WebSocketService - WebSocket connection closed.');
          onDisconnected?.call();
        },
      );

      print('DEBUG: WebSocketService - WebSocket connected successfully.');
      onConnected?.call();
    } catch (e) {
      print('ERROR: WebSocketService - Failed to connect: $e');
      onError?.call('Failed to connect: $e');
    }
  }

  Future<void> sendMessage(Map<String, dynamic> message) async {
    if (_channel == null) {
      print(
        'WARNING: WebSocketService - Channel is null, attempting to reconnect before sending.',
      );
      await connect();
      if (_channel == null) {
        print(
          'ERROR: WebSocketService - Failed to reconnect, cannot send message.',
        );
        onError?.call('WebSocket not connected, cannot send message.');
        return;
      }
    }

    try {
      final jsonMessage = jsonEncode(message);
      print('DEBUG: WebSocketService - Sending message: $jsonMessage');
      _channel!.sink.add(jsonMessage);
    } catch (e) {
      print('ERROR: WebSocketService - Failed to send message: $e');
      onError?.call('Failed to send message: $e');
    }
  }

  void disconnect() {
    print('DEBUG: WebSocketService - Disconnecting WebSocket...');
    _channel?.sink.close();
    _channel = null;
    print('DEBUG: WebSocketService - WebSocket disconnected.');
  }

  bool get isConnected => _channel != null;
}
