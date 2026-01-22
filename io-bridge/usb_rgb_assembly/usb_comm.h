#pragma once

#include <Arduino.h>
#include <stdint.h>
#include <stddef.h>

/*
Wire format (little-endian):
  uint32  magic        = USB_COMM_MAGIC
  uint16  len          = total bytes in frame including header (>= header_size)
  uint8   seq          = host-chosen sequence number
  uint8   object_id    = which object/service
  uint8   cmd_id       = which command within object
  uint8   flags        = reserved for future (0 for now)
  uint8   payload[]    = (len - header_size) bytes

Response uses the same envelope, with payload defined by the object handler.
usb_comm itself does not interpret payload contents.
*/

class UsbComm {
public:
    static constexpr uint32_t USB_COMM_MAGIC = 0xDEADBEEF;

    // You can tune these without changing the protocol.
    static constexpr size_t RX_BUFFER_SIZE = 2048;   // stream reassembly buffer
    static constexpr size_t TX_BUFFER_SIZE = 512;    // must hold header + max payload you want to return

    // Header size on the wire
    static constexpr size_t HEADER_SIZE = 4 + 2 + 1 + 1 + 1 + 1; // magic + len + seq + obj + cmd + flags

    // Parsed request view (points into rx buffer)
    struct CmdView {
        uint8_t  seq = 0;
        uint8_t  object_id = 0;
        uint8_t  cmd_id = 0;
        uint8_t  flags = 0;
        const uint8_t* payload = nullptr;
        uint16_t payload_len = 0;
    };

    // Handler return: true means "handled" (response payload is whatever you wrote).
    // false means "not handled" (usb_comm will still reply, with empty payload by default).
    using HandlerFn = bool (*)(const CmdView& cmd,
                               uint8_t* out_payload,
                               uint16_t out_max,
                               uint16_t* out_len);

    UsbComm(Stream& io,
            HandlerFn* handler_table,
            size_t handler_count);

    // Poll the stream, process AT MOST ONE complete command per call.
    // Returns true if a command was processed and a response was written.
    bool poll();

    // Optional: stats for debugging without printing
    struct Stats {
        uint32_t rx_bytes = 0;
        uint32_t frames_ok = 0;
        uint32_t frames_bad_magic = 0;
        uint32_t frames_bad_len = 0;
        uint32_t frames_no_handler = 0;
        uint32_t frames_handler_false = 0;
        uint32_t rx_overflow = 0;
        uint32_t rx_resync_drops = 0;
    };

    const Stats& stats() const { return stats_; }

private:
    Stream& io_;
    HandlerFn* handlers_;
    size_t handlers_n_;

    uint8_t rx_[RX_BUFFER_SIZE];
    size_t  rx_head_ = 0; // number of valid bytes in rx_ (always [0..rx_head_-1])

    uint8_t tx_[TX_BUFFER_SIZE];

    Stats stats_;

    // Read bytes from Stream into rx_ (bounded)
    void rx_fill_();

    // Try to locate and extract a single full frame from rx_.
    // If successful, returns true and sets cmd_view + frame_len.
    bool rx_try_get_one_frame_(CmdView& cmd_view, uint16_t& frame_len);

    // Write a response frame to io_
    void tx_send_response_(uint8_t seq,
                           uint8_t object_id,
                           uint8_t cmd_id,
                           uint8_t flags,
                           const uint8_t* payload,
                           uint16_t payload_len);

    // Helpers (LE decode/encode)
    static uint32_t le_u32_(const uint8_t* p);
    static uint16_t le_u16_(const uint8_t* p);
    static void     put_le_u32_(uint8_t* p, uint32_t v);
    static void     put_le_u16_(uint8_t* p, uint16_t v);

    // Compact buffer: drop first n bytes, shift remainder to front
    void rx_drop_(size_t n);
};
