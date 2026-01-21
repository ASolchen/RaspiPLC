#include "usb_comm.h"


UsbComm::UsbComm(Stream& serial,
                 usb_comm_out_t* outAsm,
                 usb_comm_in_t* inAsm)
: s_(serial), out_(outAsm), in_(inAsm)
{
    memset(rx_buf_, 0, sizeof(rx_buf_));
}


void UsbComm::begin() {
    memset(out_, 0, sizeof(*out_));
    memset(in_,  0, sizeof(*in_));

    out_->magic = USB_FRAME_MAGIC;
    in_->magic  = USB_FRAME_MAGIC;

    comm_ok_ = false;
    last_rx_ms_ = millis();
}


bool UsbComm::poll() {
    readAvailable_();

    // 🔒 CRITICAL FIX:
    // Extract AT MOST ONE frame per poll
    bool got_frame = tryExtractOneFrame_();

    updateTimeout_();
    return got_frame;
}


void UsbComm::readAvailable_() {
    while (s_.available()) {
        int c = s_.read();
        if (c < 0) break;

        if (rx_head_ < sizeof(rx_buf_)) {
            rx_buf_[rx_head_++] = (uint8_t)c;
        } else {
            // overflow → drop everything and resync
            rx_head_ = 0;
        }
    }
}


bool UsbComm::tryExtractOneFrame_() {
    if (rx_head_ < USB_FRAME_SIZE) {
        return false;
    }

    size_t i = 0;

    while (rx_head_ - i >= 4) {
        uint32_t magic;
        memcpy(&magic, rx_buf_ + i, sizeof(magic));

        if (magic == USB_FRAME_MAGIC) {
            if (rx_head_ - i < USB_FRAME_SIZE) {
                // Not enough bytes yet
                return false;
            }

            // Copy ONE full frame
            memcpy(out_, rx_buf_ + i, USB_FRAME_SIZE);

            // Validate
            if (out_->magic != USB_FRAME_MAGIC) {
                // Should not happen, but resync defensively
                consume_(i, 1);
                return true;
            }

            // Prepare TX response
            in_->magic = USB_FRAME_MAGIC;
            in_->watchdog_in = out_->watchdog_out + 1;

            // Transmit response
            s_.write((const uint8_t*)in_, USB_FRAME_SIZE);

            comm_ok_ = true;
            last_rx_ms_ = millis();

            // Remove ONLY this frame from buffer
            consume_(i, USB_FRAME_SIZE);

            return true;   // EXACTLY ONE FRAME
        }

        i++;
    }

    // Discard scanned bytes that cannot start a frame
    if (i > 0 && i < rx_head_) {
        memmove(rx_buf_, rx_buf_ + i, rx_head_ - i);
        rx_head_ -= i;
    }

    return false;
}


void UsbComm::consume_(size_t start, size_t len) {
    size_t end = start + len;
    if (end > rx_head_) end = rx_head_;

    size_t remaining = rx_head_ - end;
    memmove(rx_buf_, rx_buf_ + end, remaining);
    rx_head_ = remaining;
}


void UsbComm::updateTimeout_() {
    if ((uint32_t)(millis() - last_rx_ms_) > timeout_ms_) {
        comm_ok_ = false;
    }
}


bool UsbComm::commOk() const {
    return comm_ok_;
}


void UsbComm::setTimeoutMs(uint32_t ms) {
    timeout_ms_ = ms;
}
