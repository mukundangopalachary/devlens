package main

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type focusPane int

const (
	paneChat focusPane = iota
	paneContext
	paneTasks
	paneSkills
	paneStatus
)

type commandResultMsg struct {
	name    string
	content string
	err     error
}

type model struct {
	width         int
	height        int
	focus         focusPane
	statusLine    string
	chatInput     string
	chatLog       []string
	contextLines  []string
	taskLines     []string
	skillLines    []string
	errorLine     string
	sessions      []sessionItem
	selectedIndex int
	activeSession int
	showPicker    bool
	showHelp      bool
	ingestInput   string
	showIngest    bool
}

type sessionItem struct {
	id    int
	title string
	when  string
}

func newModel() model {
	return model{
		focus:         paneChat,
		statusLine:    "tab pane | q quit | ctrl+s sessions | ctrl+o ingest | ? help",
		chatLog:       []string{"Welcome. Type question. Press enter."},
		contextLines:  []string{"No context loaded yet."},
		taskLines:     []string{"No tasks loaded yet."},
		skillLines:    []string{"No skills loaded yet."},
		sessions:      []sessionItem{{id: 1, title: "session-1", when: "unknown"}},
		activeSession: 1,
	}
}

func (m model) Init() tea.Cmd {
	return tea.Batch(
		fetchCommand("tasks", []string{"tasks", "--json"}),
		fetchCommand("skills", []string{"skills", "--json"}),
		fetchCommand("sessions", []string{"sessions", "--json"}),
	)
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		return m, nil
	case tea.KeyMsg:
		return m.handleKey(msg)
	case commandResultMsg:
		if msg.err != nil {
			m.errorLine = fmt.Sprintf("%s failed: %v", msg.name, msg.err)
			return m, nil
		}
		m.consumeCommandResult(msg)
		return m, nil
	default:
		return m, nil
	}
}

func (m model) handleKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	if msg.Type == tea.KeyRunes {
		value := string(msg.Runes)
		if m.showIngest {
			m.ingestInput += value
			return m, nil
		}
		if m.focus == paneChat {
			m.chatInput += value
		}
		return m, nil
	}

	switch msg.String() {
	case "q", "ctrl+c":
		return m, tea.Quit
	case "tab":
		m.focus = (m.focus + 1) % 5
		return m, nil
	case "shift+tab":
		if m.focus == 0 {
			m.focus = 4
		} else {
			m.focus--
		}
		return m, nil
	case "ctrl+s":
		m.showPicker = !m.showPicker
		m.showHelp = false
		m.showIngest = false
		return m, fetchCommand("sessions", []string{"sessions", "--json"})
	case "ctrl+o":
		m.showIngest = !m.showIngest
		m.showHelp = false
		m.showPicker = false
		return m, nil
	case "?", "f1":
		m.showHelp = !m.showHelp
		m.showPicker = false
		m.showIngest = false
		return m, nil
	case "down":
		if m.showPicker && m.selectedIndex < len(m.sessions)-1 {
			m.selectedIndex++
		}
		return m, nil
	case "up":
		if m.showPicker && m.selectedIndex > 0 {
			m.selectedIndex--
		}
		return m, nil
	case "enter":
		if m.showPicker {
			m.activeSession = m.sessions[m.selectedIndex].id
			m.statusLine = fmt.Sprintf("Selected session #%d", m.activeSession)
			m.showPicker = false
			return m, nil
		}
		if m.showIngest {
			target := strings.TrimSpace(m.ingestInput)
			if target == "" {
				m.statusLine = "ingest path empty"
				return m, nil
			}
			m.statusLine = "ingest request sent"
			m.showIngest = false
			cmd := fetchCommand("ingest", []string{"ingest", target, "--json"})
			m.ingestInput = ""
			return m, cmd
		}
		if strings.TrimSpace(m.chatInput) == "" {
			return m, nil
		}
		m.chatLog = append(m.chatLog, "you> "+m.chatInput)
		m.statusLine = "chat request sent"
		cmd := fetchCommand(
			"ask",
			[]string{"ask", m.chatInput, "--session-id", fmt.Sprintf("%d", m.activeSession), "--json"},
		)
		m.chatInput = ""
		return m, cmd
	case "ctrl+r":
		return m, tea.Batch(
			fetchCommand("tasks", []string{"tasks", "--json"}),
			fetchCommand("skills", []string{"skills", "--json"}),
			fetchCommand("sessions", []string{"sessions", "--json"}),
		)
	case "backspace":
		if m.showIngest {
			if len(m.ingestInput) > 0 {
				m.ingestInput = m.ingestInput[:len(m.ingestInput)-1]
			}
			return m, nil
		}
		if len(m.chatInput) > 0 {
			m.chatInput = m.chatInput[:len(m.chatInput)-1]
		}
		return m, nil
	case "space":
		if m.showIngest {
			m.ingestInput += " "
			return m, nil
		}
		if m.focus == paneChat {
			m.chatInput += " "
		}
		return m, nil
	default:
		return m, nil
	}
}

func (m *model) consumeCommandResult(msg commandResultMsg) {
	if msg.name == "tasks" {
		m.taskLines = readLinesFromJSON(msg.content, "data.items", "title")
		if len(m.taskLines) == 0 {
			m.taskLines = []string{"No tasks"}
		}
		return
	}
	if msg.name == "skills" {
		m.skillLines = readLinesFromJSON(msg.content, "data.skills", "name")
		if len(m.skillLines) == 0 {
			m.skillLines = []string{"No skills"}
		}
		return
	}
	if msg.name == "ask" {
		reply := readValueFromJSON(msg.content, "data.reply")
		if reply == "" {
			m.chatLog = append(m.chatLog, "agent> [empty]")
		} else {
			m.chatLog = append(m.chatLog, "agent> "+reply)
		}
		citations := readArrayFromJSON(msg.content, "data.citations")
		if len(citations) > 0 {
			m.contextLines = citations
		}
		m.statusLine = "chat response received"
		return
	}
	if msg.name == "sessions" {
		sessions := readSessionsFromJSON(msg.content)
		if len(sessions) > 0 {
			m.sessions = sessions
			if m.selectedIndex >= len(m.sessions) {
				m.selectedIndex = len(m.sessions) - 1
			}
		}
		return
	}
	if msg.name == "ingest" {
		loaded := readIntFromJSON(msg.content, "data.loaded_count")
		m.statusLine = fmt.Sprintf("ingested %d file(s)", loaded)
		return
	}
}

func (m model) View() string {
	if m.width == 0 || m.height == 0 {
		return "Initializing TUI..."
	}
	panelStyle := lipgloss.NewStyle().Border(lipgloss.NormalBorder()).Padding(0, 1)
	focusStyle := lipgloss.NewStyle().BorderForeground(lipgloss.Color("42"))

	chat := panelStyle.Width(m.width / 2).Render(
		strings.Join(append(m.chatLog, "", "input> "+m.chatInput), "\n"),
	)
	if m.focus == paneChat {
		chat = focusStyle.Width(m.width / 2).Render(chat)
	}

	rightWidth := m.width - (m.width / 2) - 4
	context := panelStyle.Width(rightWidth).Render("Context\n" + strings.Join(m.contextLines, "\n"))
	tasks := panelStyle.Width(rightWidth).Render("Tasks\n" + strings.Join(m.taskLines, "\n"))
	skills := panelStyle.Width(rightWidth).Render("Skills\n" + strings.Join(m.skillLines, "\n"))
	status := panelStyle.Width(rightWidth).Render("Status\n" + m.statusLine + "\n" + m.errorLine)

	right := lipgloss.JoinVertical(lipgloss.Top, context, tasks, skills, status)
	main := lipgloss.JoinHorizontal(lipgloss.Top, chat, right)

	if m.showPicker {
		pickerLines := []string{"Session Picker"}
		for idx, session := range m.sessions {
			prefix := "  "
			if idx == m.selectedIndex {
				prefix = "> "
			}
			pickerLines = append(
				pickerLines,
				fmt.Sprintf("%s#%d %s (%s)", prefix, session.id, session.title, session.when),
			)
		}
		picker := panelStyle.Width(m.width - 4).Render(strings.Join(pickerLines, "\n"))
		return lipgloss.JoinVertical(lipgloss.Top, main, picker)
	}

	if m.showIngest {
		ingest := panelStyle.Width(m.width - 4).Render(
			"Ingest Picker\nEnter file path and press Enter\n" + m.ingestInput,
		)
		return lipgloss.JoinVertical(lipgloss.Top, main, ingest)
	}

	if m.showHelp {
		help := panelStyle.Width(m.width - 4).Render(strings.Join([]string{
			"Shortcuts",
			"q: quit",
			"tab / shift+tab: switch focus pane",
			"ctrl+r: refresh tasks/skills/sessions",
			"ctrl+s: session picker",
			"ctrl+o: ingest file picker",
			"?: help toggle",
		}, "\n"))
		return lipgloss.JoinVertical(lipgloss.Top, main, help)
	}

	return main
}

func fetchCommand(name string, args []string) tea.Cmd {
	return func() tea.Msg {
		command := exec.Command("uv", append([]string{"run", "devlens"}, args...)...)
		command.Dir = detectRepoRoot()
		output, err := command.CombinedOutput()
		return commandResultMsg{name: name, content: string(output), err: err}
	}
}

func detectRepoRoot() string {
	wd, err := os.Getwd()
	if err != nil {
		return "."
	}
	candidate := wd
	for {
		if _, err := os.Stat(filepath.Join(candidate, "pyproject.toml")); err == nil {
			return candidate
		}
		parent := filepath.Dir(candidate)
		if parent == candidate {
			return wd
		}
		candidate = parent
	}
}

func readValueFromJSON(content string, dottedPath string) string {
	paths := strings.Split(dottedPath, ".")
	var data map[string]any
	if err := json.Unmarshal([]byte(content), &data); err != nil {
		return ""
	}
	var current any = data
	for _, key := range paths {
		obj, ok := current.(map[string]any)
		if !ok {
			return ""
		}
		current = obj[key]
	}
	value, ok := current.(string)
	if !ok {
		return ""
	}
	return value
}

func readArrayFromJSON(content string, dottedPath string) []string {
	paths := strings.Split(dottedPath, ".")
	var data map[string]any
	if err := json.Unmarshal([]byte(content), &data); err != nil {
		return nil
	}
	var current any = data
	for _, key := range paths {
		obj, ok := current.(map[string]any)
		if !ok {
			return nil
		}
		current = obj[key]
	}
	rawArr, ok := current.([]any)
	if !ok {
		return nil
	}
	out := make([]string, 0, len(rawArr))
	for _, item := range rawArr {
		if str, ok := item.(string); ok {
			out = append(out, str)
		}
	}
	return out
}

func readLinesFromJSON(content string, arrPath string, key string) []string {
	paths := strings.Split(arrPath, ".")
	var data map[string]any
	if err := json.Unmarshal([]byte(content), &data); err != nil {
		return nil
	}
	var current any = data
	for _, path := range paths {
		obj, ok := current.(map[string]any)
		if !ok {
			return nil
		}
		current = obj[path]
	}
	rawArr, ok := current.([]any)
	if !ok {
		return nil
	}
	lines := make([]string, 0, len(rawArr))
	for _, row := range rawArr {
		obj, ok := row.(map[string]any)
		if !ok {
			continue
		}
		value, ok := obj[key].(string)
		if !ok || strings.TrimSpace(value) == "" {
			continue
		}
		lines = append(lines, value)
	}
	return lines
}

func readIntFromJSON(content string, dottedPath string) int {
	paths := strings.Split(dottedPath, ".")
	var data map[string]any
	if err := json.Unmarshal([]byte(content), &data); err != nil {
		return 0
	}
	var current any = data
	for _, key := range paths {
		obj, ok := current.(map[string]any)
		if !ok {
			return 0
		}
		current = obj[key]
	}
	switch value := current.(type) {
	case float64:
		return int(value)
	case int:
		return value
	default:
		return 0
	}
}

func readSessionsFromJSON(content string) []sessionItem {
	paths := []string{"data", "items"}
	var data map[string]any
	if err := json.Unmarshal([]byte(content), &data); err != nil {
		return nil
	}
	var current any = data
	for _, path := range paths {
		obj, ok := current.(map[string]any)
		if !ok {
			return nil
		}
		current = obj[path]
	}
	rawArr, ok := current.([]any)
	if !ok {
		return nil
	}
	items := make([]sessionItem, 0, len(rawArr))
	for _, row := range rawArr {
		obj, ok := row.(map[string]any)
		if !ok {
			continue
		}
		id, _ := obj["id"].(float64)
		title, _ := obj["title"].(string)
		when, _ := obj["created_at"].(string)
		items = append(items, sessionItem{id: int(id), title: title, when: when})
	}
	return items
}
