STATUS_CONNECTED = 'connected'
STATUS_CONNECTING = 'connecting'
STATUS_INACTIVE = 'inactive'
STATUS_DISCONNECTED = 'disconnected'
STATUS_SCANNING = 'scanning'

# Translate status from daemon to constants.
STATUS_CONSTS = {
    'completed': STATUS_CONNECTED,
    'inactive': STATUS_INACTIVE,
    'authenticating': STATUS_CONNECTING,
    'associating': STATUS_CONNECTING,
    'associated': STATUS_CONNECTING,
    '4way_handshake': STATUS_CONNECTING,
    'group_handshake': STATUS_CONNECTING,
    'interface_disabled': STATUS_INACTIVE,
    'disconnected': STATUS_DISCONNECTED,
    'scanning': STATUS_SCANNING,
}
