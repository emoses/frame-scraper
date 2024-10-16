package hassconnection

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"maps"
	"os"
	"sync"

	"github.com/gorilla/websocket"
)

type Config struct {
	Address string
	Token   string
}

type Message struct {
	Type   string `json:"type"`
	Fields map[string]any
}

func (m *Message) UnmarshalJSON(data []byte) error {
	if err := json.Unmarshal(data, &m.Fields); err != nil {
		return err
	}
	typ, ok := m.Fields["type"]
	if !ok {
		return errors.New("Missing type field in message")
	}
	strType, ok := typ.(string)
	if !ok {
		return errors.New("Unexpected type for 'type' field in message")
	}
	m.Type = strType
	delete(m.Fields, "type")

	return nil
}
func (m *Message) MarshalJSON() ([]byte, error) {
	mm := maps.Clone(m.Fields)
	mm["type"] = m.Type
	return json.Marshal(mm)
}

type AuthRequired struct {
	Type string `json:"type"`
}

type Auth struct {
	Type        string `json:"type"`
	AccessToken string `json:"access_token"`
}

type connState string

const (
	connStateNew          connState = "new"
	connStateAuth         connState = "auth"
	connStateConnected    connState = "connected"
	connStateDisconnected connState = "disconnected"
)

var (
	ErrAuthFailed = errors.New("Authentication failed")
)

type MessageHandler func(*Message)

type HassConnection struct {
	sync.Mutex
	conn     *websocket.Conn
	connErr  error
	state    connState
	config   *Config
	messages map[int]MessageHandler
	incoming <-chan *Message
	outgoing chan<- *Message
	nextId   int
	ready    chan struct{}
}

func (h *HassConnection) readMessage() (*Message, error) {
	data := &Message{}
	if err := h.conn.ReadJSON(data); err != nil {
		return nil, fmt.Errorf("Error parsing websocket message: %w", err)
	}

	return data, nil
}

func (h *HassConnection) connReader(ctx context.Context) <-chan *Message {
	incoming := make(chan *Message)

	go func() {
		defer close(incoming)
		for {
			select {
			case <-ctx.Done():
				return
			default:
			}
			msg, err := h.readMessage()
			if err != nil {
				fmt.Fprintf(os.Stderr, "Error reading message: %s", err.Error())
				h.Lock()
				h.setState(connStateDisconnected)
				h.connErr = err
				h.Unlock()
				return
			}
			select {
			case <-ctx.Done():
				return
			case incoming <- msg:
			}
		}
	}()

	return incoming
}

func (h *HassConnection) connWriter(ctx context.Context) chan<- *Message {
	outgoing := make(chan *Message)

	go func() {
		defer close(outgoing)
		for {
			var msg *Message
			select {
			case <-ctx.Done():
				return
			case msg = <-outgoing:
			}

			if err := h.conn.WriteJSON(msg); err != nil {
				fmt.Fprintf(os.Stderr, "Error writing message: %s", err.Error())
				h.Lock()
				h.setState(connStateDisconnected)
				h.connErr = err
				h.Unlock()
				return
			}
		}
	}()

	return outgoing
}

func (h *HassConnection) Connect(ctx context.Context) error {
	conn, resp, err := websocket.DefaultDialer.DialContext(ctx, h.config.Address, nil)
	if err != nil {
		return fmt.Errorf("Error connecting: %w", err)
	}

	h.Lock()
	defer h.Unlock()
	slog.Debug("Connected", "resp", resp)

	h.conn = conn
	h.setState(connStateAuth)

	return nil
}

func (h *HassConnection) Close() error {
	if h.conn != nil {
		err := h.conn.Close()
		h.conn = nil
		return err
	}
	return nil
}

func (h *HassConnection) Run(ctx context.Context) error {
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	if err := h.Connect(ctx); err != nil {
		return err
	}

	incoming := h.connReader(ctx)
	outgoing := h.connWriter(ctx)
	h.Lock()
	h.incoming = incoming
	h.outgoing = outgoing
	h.Unlock()

	msg := <-incoming
	if msg.Type != "auth_required" {
		return fmt.Errorf("Unexpected initial message %+v", msg)
	}

	outgoing <- &Message{
		Type: "auth",
		Fields: map[string]any{
			"access_token": h.config.Token,
		},
	}

	msg = <-incoming
	switch msg.Type {
	case "auth_ok":
		slog.Debug("Auth_ok")
		h.Lock()
		h.setState(connStateConnected)
		h.Unlock()
	case "auth_invalid":
		slog.Warn("Auth_invalid")
		return ErrAuthFailed
	}

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case msg := <-h.incoming:
			h.handleMessage(msg)
		}
	}
}

func (h *HassConnection) handleMessage(msg *Message) {
	id, ok := msg.Fields["id"]
	if !ok {
		slog.Debug("No id field")
		return
	}

	idNum, ok := id.(float64)
	if !ok {
		return
	}
	idInt := int(idNum)
	slog.Debug("Got message id", "id", idInt)

	if handler, ok := h.messages[idInt]; ok {
		slog.Debug("Found handler for id", "id", idInt)
		handler(msg)
	}
}

func (h *HassConnection) subscriptionHandler(c chan *Message) MessageHandler {
	return func(msg *Message) {
		// This will block if we're not careful
		c <- msg
	}
}

func (h *HassConnection) resultHandler(id int, next MessageHandler) (MessageHandler, <-chan error) {
	result := make(chan error, 1)

	return func(msg *Message) {
		if msg.Type != "result" {
			slog.Debug("unexpected message for id", "id", id, "msg", msg)
			return
		}
		if !msg.Fields["success"].(bool) {
			slog.Debug("Subscribe failure", "result", msg.Fields["error"])
			result <- fmt.Errorf("subscribe failed, %v", msg.Fields["error"])
			next = nil
		}

		h.Lock()
		defer h.Unlock()
		if next != nil {
			h.messages[id] = next
		} else {
			delete(h.messages, id)
		}

		close(result)
	}, result
}

func (h *HassConnection) getNextId() int {
	h.Lock()
	defer h.Unlock()
	h.nextId += 1
	return h.nextId
}

func (h *HassConnection) unsubscribe(subId int) <-chan error {
	id := h.getNextId()
	return h.sendCommand(id,
		&Message{
			Type: "unsubscribe_events",
			Fields: map[string]any{
				"id":           id,
				"subscription": subId,
			},
		},
		nil)
}

func (h *HassConnection) Ready() <-chan struct{} {
	h.Lock()
	if h.ready == nil {
		h.ready = make(chan struct{})
		if h.state == connStateConnected {
			close(h.ready)
		}
	}
	h.Unlock()

	return h.ready
}

// call with lock held
func (h *HassConnection) setState(s connState) {
	h.state = s
	if h.ready != nil && s == connStateConnected {
		close(h.ready)
	}
}

func (h *HassConnection) sendCommand(id int, msg *Message, handler MessageHandler) <-chan error {
	var errC <-chan error
	h.Lock()
	h.messages[id], errC = h.resultHandler(id, handler)
	h.Unlock()

	msg.Fields["id"] = id
	h.outgoing <- msg
	return errC
}

type cmdResult struct {
	err    error
	result any
}

func (h *HassConnection) sendCommandResult(id int, msg *Message) <-chan cmdResult {

	result := make(chan cmdResult)
	h.Lock()
	h.messages[id] = func(msg *Message) {
		if msg.Type != "result" {
			slog.Debug("unexpected message for id", "id", id, "msg", msg)
			return
		}
		if !msg.Fields["success"].(bool) {
			slog.Debug("Command failure", "result", msg.Fields["error"])
			result <- cmdResult{
				err: fmt.Errorf("command failed, %v", msg.Fields["error"]),
			}
		} else {
			result <- cmdResult{
				result: msg.Fields["result"],
			}
		}

		h.Lock()
		defer h.Unlock()
		delete(h.messages, id)

		close(result)
	}
	h.Unlock()

	msg.Fields["id"] = id
	h.outgoing <- msg
	return result
}

func (h *HassConnection) Subscribe(eventType string) (<-chan *Message, func(), error) {
	messages := make(chan *Message)

	slog.Debug("Subscribing to event", "event_type", eventType)

	id := h.getNextId()
	msg := &Message{
		Type: "subscribe_events",
		Fields: map[string]any{
			"id":         id,
			"event_type": eventType,
		},
	}
	subErr := h.sendCommand(id, msg, h.subscriptionHandler(messages))

	closer := func() {
		slog.Debug("Unsubscribing to event", "event_type", eventType)
		res := h.unsubscribe(id)
		if err := <-res; err != nil {
			fmt.Fprintf(os.Stderr, "Error unsubscribing from %s (%d): %v", eventType, id, err)
		}
		close(messages)
	}

	//TODO: async?
	if err := <-subErr; err != nil {
		close(messages)
		return nil, nil, err
	}

	return messages, closer, nil
}

func (h *HassConnection) GetStates() ([]map[string]any, error) {
	slog.Debug("Getting state")

	id := h.getNextId()
	statesC := h.sendCommandResult(id,
		&Message{
			Type: "get_states",
			Fields: map[string]any{
				"id": id,
			},
		},
	)
	cmdResult := <-statesC
	if cmdResult.err != nil {
		return nil, fmt.Errorf("Error from get_state: %w", cmdResult.err)
	}

	resultSlice := cmdResult.result.([]any)
	result := make([]map[string]any, len(resultSlice))
	for i, res := range resultSlice {
		result[i] = res.(map[string]any)
	}

	return result, nil
}

func New(config *Config) *HassConnection {
	return &HassConnection{
		state:    connStateNew,
		config:   config,
		messages: map[int]MessageHandler{},
	}
}
