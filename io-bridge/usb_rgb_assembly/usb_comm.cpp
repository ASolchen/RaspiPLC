#include "usb_comm.h"
#include <string.h>

UsbComm::UsbComm(Stream& io,
                 HandlerFn* handler_table,
                 size_t handler_count)
: io_(io),
  handlers_(handler_table),
  handlers_n_(handler_count)
{
    memset(rx_, 0, sizeof(rx_));
    memset(tx_, 0, sizeof(tx_));
    rx_head_ = 0;
    memset(&stats_, 0, sizeof(stats_));
}

bool UsbComm::poll()
{
    // 1) Pull in any available bytes (non-blocking style).
    rx_fill_();

    // 2) Attempt to extract ONE complete frame.
    CmdView cmd;
    uint16_t frame_len = 0;
    if (!rx_try_get_one_frame_(cmd, frame_len)) {
        return false; // nothing complete yet
    }

    // At this point, cmd.payload points into rx_ memory. Before we drop/compact rx_,
    // we must handle the command (handlers should copy what they need immediately).
    uint16_t out_len = 0;
    uint8_t* out_payload = tx_ + HEADER_SIZE;
    uint16_t out_max = (TX_BUFFER_SIZE >= HEADER_SIZE) ? (uint16_t)(TX_BUFFER_SIZE - HEADER_SIZE) : 0;

    bool handled = false;
    if (cmd.object_id < handlers_n_ && handlers_[cmd.object_id]) {
        handled = handlers_[cmd.object_id](cmd, out_payload, out_max, &out_len);
        if (!handled) stats_.frames_handler_false++;
    } else {
        stats_.frames_no_handler++;
        handled = false;
        out_len = 0;
    }

    // 3) Send response. usb_comm doesn't define semantics; it just mirrors envelope.
    // If handler returned false, response payload is empty by default.
    // (You can choose to have handlers always return true and encode errors in payload.)
    tx_send_response_(cmd.seq, cmd.object_id, cmd.cmd_id, cmd.flags, out_payload, out_len);

    stats_.frames_ok++;
    return true;
}

void UsbComm::rx_fill_()
{
    // Read as much as will fit without overflow.
    while (io_.available() > 0) {
        if (rx_head_ >= RX_BUFFER_SIZE) {
            // Overflow: drop everything to resync cleanly
            rx_head_ = 0;
            stats_.rx_overflow++;
            // Drain one byte to move forward
            (void)io_.read();
            continue;
        }
        int c = io_.read();
        if (c < 0) break;
        rx_[rx_head_++] = (uint8_t)c;
        stats_.rx_bytes++;
    }
}

bool UsbComm::rx_try_get_one_frame_(CmdView& cmd_view, uint16_t& frame_len)
{
    // We need at least a header to do anything.
    if (rx_head_ < HEADER_SIZE) return false;

    // Scan for MAGIC. If not at index 0, drop bytes until it is (resync).
    // Note: this is O(n), but RX_BUFFER_SIZE is small and poll is frequent.
    size_t i = 0;
    while (i + 4 <= rx_head_) {
        if (le_u32_(rx_ + i) == USB_COMM_MAGIC) break;
        i++;
    }

    if (i > 0) {
        // Drop bytes before magic (or all if magic not found)
        rx_drop_(i);
        stats_.rx_resync_drops += (uint32_t)i;
    }

    if (rx_head_ < HEADER_SIZE) return false;
    if (le_u32_(rx_) != USB_COMM_MAGIC) {
        // Magic not found even after drop; drop one byte and try later
        rx_drop_(1);
        stats_.frames_bad_magic++;
        return false;
    }

    uint16_t len = le_u16_(rx_ + 4);
    if (len < HEADER_SIZE) {
        // Invalid length; drop magic byte and resync
        rx_drop_(1);
        stats_.frames_bad_len++;
        return false;
    }

    if (len > RX_BUFFER_SIZE) {
        // Unreasonably large frame; drop magic byte and resync
        rx_drop_(1);
        stats_.frames_bad_len++;
        return false;
    }

    if (rx_head_ < len) {
        // Not enough bytes yet for full frame
        return false;
    }

    // Parse header fields
    cmd_view.seq       = rx_[6];
    cmd_view.object_id = rx_[7];
    cmd_view.cmd_id    = rx_[8];
    cmd_view.flags     = rx_[9];

    cmd_view.payload = rx_ + HEADER_SIZE;
    cmd_view.payload_len = (uint16_t)(len - HEADER_SIZE);

    frame_len = len;

    // Now that we have a full frame, we can drop it from rx_ AFTER caller uses payload.
    // However caller handles immediately and then we can drop now.
    rx_drop_(len);

    return true;
}

void UsbComm::tx_send_response_(uint8_t seq,
                               uint8_t object_id,
                               uint8_t cmd_id,
                               uint8_t flags,
                               const uint8_t* payload,
                               uint16_t payload_len)
{
    // Cap payload to TX buffer capacity.
    uint16_t max_payload = (TX_BUFFER_SIZE > HEADER_SIZE) ? (uint16_t)(TX_BUFFER_SIZE - HEADER_SIZE) : 0;
    if (payload_len > max_payload) payload_len = max_payload;

    // Build header
    put_le_u32_(tx_, USB_COMM_MAGIC);
    put_le_u16_(tx_ + 4, (uint16_t)(HEADER_SIZE + payload_len));
    tx_[6] = seq;
    tx_[7] = object_id;
    tx_[8] = cmd_id;
    tx_[9] = flags;

    // Copy payload
    if (payload_len > 0 && payload) {
        memcpy(tx_ + HEADER_SIZE, payload, payload_len);
    }

    // Write exactly len bytes
    const size_t total = (size_t)(HEADER_SIZE + payload_len);
    io_.write(tx_, total);
    io_.flush(); // CDC: flush pushes to USB stack/host buffers
}

uint32_t UsbComm::le_u32_(const uint8_t* p)
{
    return ((uint32_t)p[0]) |
           ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

uint16_t UsbComm::le_u16_(const uint8_t* p)
{
    return (uint16_t)(((uint16_t)p[0]) | ((uint16_t)p[1] << 8));
}

void UsbComm::put_le_u32_(uint8_t* p, uint32_t v)
{
    p[0] = (uint8_t)(v & 0xFF);
    p[1] = (uint8_t)((v >> 8) & 0xFF);
    p[2] = (uint8_t)((v >> 16) & 0xFF);
    p[3] = (uint8_t)((v >> 24) & 0xFF);
}

void UsbComm::put_le_u16_(uint8_t* p, uint16_t v)
{
    p[0] = (uint8_t)(v & 0xFF);
    p[1] = (uint8_t)((v >> 8) & 0xFF);
}

void UsbComm::rx_drop_(size_t n)
{
    if (n == 0) return;
    if (n >= rx_head_) {
        rx_head_ = 0;
        return;
    }
    // Shift remaining bytes down to index 0
    memmove(rx_, rx_ + n, rx_head_ - n);
    rx_head_ -= n;
}
