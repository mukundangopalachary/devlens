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
	errorHistory  []string
	sessions      []sessionItem
	selectedIndex int
	activeSession int
	showPicker    bool
	showHelp      bool
	ingestInput   string
	showIngest    bool
	// Scrolling
	chatScroll    int
	contextScroll int
	taskScroll    int
	skillScroll   int
	// Loading
	loading map[string]bool
	// Task selection
	taskSelectedIdx int
	taskIDs         []int
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
		loading:       map[string]bool{},
	}
}

func (m model) Init() tea.Cmd {
	m.loading["tasks"] = true
	m.loading["skills"] = true
	m.loading["sessions"] = true
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
		delete(m.loading, msg.name)
		if msg.err != nil {
			errMsg := fmt.Sprintf("%s failed: %v", msg.name, msg.err)
			m.errorLine = errMsg
			m.errorHistory = append(m.errorHistory, errMsg)
			if len(m.errorHistory) > 20 {
				m.errorHistory = m.errorHistory[1:]
			}
			return m, nil
		}
		m.consumeCommandResult(msg)
		return m, nil
	default:
		return m, nil
	}
}

func (m model) handleKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	// Text input for ingest/chat
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
	case "esc":
		m.showPicker = false
		m.showHelp = false
		m.showIngest = false
		return m, nil
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
	case "ctrl+a":
		m.statusLine = "analyze request sent"
		m.loading["analyze"] = true
		return m, fetchCommand("analyze", []string{"analyze", ".", "--json"})
	case "?", "f1":
		m.showHelp = !m.showHelp
		m.showPicker = false
		m.showIngest = false
		return m, nil
	case "j", "down":
		if m.showPicker {
			if m.selectedIndex < len(m.sessions)-1 {
				m.selectedIndex++
			}
			return m, nil
		}
		if m.focus == paneTasks && len(m.taskIDs) > 0 {
			if m.taskSelectedIdx < len(m.taskIDs)-1 {
				m.taskSelectedIdx++
			}
			return m, nil
		}
		m.scrollDown()
		return m, nil
	case "k", "up":
		if m.showPicker {
			if m.selectedIndex > 0 {
				m.selectedIndex--
			}
			return m, nil
		}
		if m.focus == paneTasks && len(m.taskIDs) > 0 {
			if m.taskSelectedIdx > 0 {
				m.taskSelectedIdx--
			}
			return m, nil
		}
		m.scrollUp()
		return m, nil
	case "pgdown":
		for i := 0; i < 5; i++ {
			m.scrollDown()
		}
		return m, nil
	case "pgup":
		for i := 0; i < 5; i++ {
			m.scrollUp()
		}
		return m, nil
	case "d":
		if m.focus == paneTasks && len(m.taskIDs) > 0 {
			taskID := m.taskIDs[m.taskSelectedIdx]
			m.statusLine = fmt.Sprintf("marking task #%d done", taskID)
			m.loading["tasks"] = true
			return m, tea.Batch(
				fetchCommand("task-done", []string{"tasks", "--done", fmt.Sprintf("%d", taskID), "--json"}),
				fetchCommand("tasks", []string{"tasks", "--json"}),
			)
		}
		return m, nil
	case "x":
		if m.focus == paneTasks && len(m.taskIDs) > 0 {
			taskID := m.taskIDs[m.taskSelectedIdx]
			m.statusLine = fmt.Sprintf("removing task #%d", taskID)
			m.loading["tasks"] = true
			return m, tea.Batch(
				fetchCommand("task-remove", []string{"tasks", "--remove", fmt.Sprintf("%d", taskID), "--json"}),
				fetchCommand("tasks", []string{"tasks", "--json"}),
			)
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
			m.loading["ingest"] = true
			cmd := fetchCommand("ingest", []string{"ingest", target, "--json"})
			m.ingestInput = ""
			return m, cmd
		}
		if strings.TrimSpace(m.chatInput) == "" {
			return m, nil
		}
		m.chatLog = append(m.chatLog, "you> "+m.chatInput)
		m.statusLine = "chat request sent"
		m.loading["ask"] = true
		cmd := fetchCommand(
			"ask",
			[]string{"ask", m.chatInput, "--session-id", fmt.Sprintf("%d", m.activeSession), "--json"},
		)
		m.chatInput = ""
		m.chatScroll = max(0, len(m.chatLog)-10)
		return m, cmd
	case "ctrl+r":
		m.loading["tasks"] = true
		m.loading["skills"] = true
		m.loading["sessions"] = true
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

func (m *model) scrollDown() {
	switch m.focus {
	case paneChat:
		if m.chatScroll < len(m.chatLog)-1 {
			m.chatScroll++
		}
	case paneContext:
		if m.contextScroll < len(m.contextLines)-1 {
			m.contextScroll++
		}
	case paneTasks:
		if m.taskScroll < len(m.taskLines)-1 {
			m.taskScroll++
		}
	case paneSkills:
		if m.skillScroll < len(m.skillLines)-1 {
			m.skillScroll++
		}
	}
}

func (m *model) scrollUp() {
	switch m.focus {
	case paneChat:
		if m.chatScroll > 0 {
			m.chatScroll--
		}
	case paneContext:
		if m.contextScroll > 0 {
			m.contextScroll--
		}
	case paneTasks:
		if m.taskScroll > 0 {
			m.taskScroll--
		}
	case paneSkills:
		if m.skillScroll > 0 {
			m.skillScroll--
		}
	}
}

func (m *model) consumeCommandResult(msg commandResultMsg) {
	if msg.name == "tasks" {
		m.taskLines = readLinesFromJSON(msg.content, "data.items", "title")
		m.taskIDs = readIDsFromJSON(msg.content, "data.items")
		if len(m.taskLines) == 0 {
			m.taskLines = []string{"No tasks"}
			m.taskIDs = nil
		}
		if m.taskSelectedIdx >= len(m.taskIDs) && len(m.taskIDs) > 0 {
			m.taskSelectedIdx = len(m.taskIDs) - 1
		}
		return
	}
	if msg.name == "task-done" || msg.name == "task-remove" {
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
		m.chatScroll = max(0, len(m.chatLog)-10)
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
	if msg.name == "analyze" {
		analyzed := readIntFromJSON(msg.content, "data.files_analyzed")
		m.statusLine = fmt.Sprintf("analyzed %d file(s)", analyzed)
		return
	}
}

func visibleSlice(lines []string, offset int, maxLines int) []string {
	if offset >= len(lines) {
		offset = max(0, len(lines)-1)
	}
	end := offset + maxLines
	if end > len(lines) {
		end = len(lines)
	}
	return lines[offset:end]
}

func (m model) View() string {
	if m.width == 0 || m.height == 0 {
		return "Initializing TUI..."
	}

	accentColor := lipgloss.Color("42")
	errColor := lipgloss.Color("196")
	dimColor := lipgloss.Color("240")

	panelStyle := lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(0, 1)
	focusStyle := panelStyle.BorderForeground(accentColor)
	headerStyle := lipgloss.NewStyle().Bold(true).Foreground(accentColor)
	loadingStyle := lipgloss.NewStyle().Foreground(dimColor).Italic(true)
	errStyle := lipgloss.NewStyle().Foreground(errColor).Bold(true)

	paneHeight := max(4, (m.height-6)/4)
	chatHeight := max(6, m.height-6)

	// Chat pane
	chatVisible := visibleSlice(m.chatLog, m.chatScroll, chatHeight-3)
	chatContent := strings.Join(append(chatVisible, "", "input> "+m.chatInput), "\n")
	chatHeader := headerStyle.Render("Chat")
	if m.loading["ask"] {
		chatHeader += " " + loadingStyle.Render("⟳")
	}
	style := panelStyle
	if m.focus == paneChat {
		style = focusStyle
	}
	chat := style.Width(m.width/2).Height(chatHeight).Render(chatHeader + "\n" + chatContent)

	rightWidth := m.width - (m.width / 2) - 4

	// Context pane
	ctxHeader := headerStyle.Render("Context")
	ctxVisible := visibleSlice(m.contextLines, m.contextScroll, paneHeight-1)
	ctxStyle := panelStyle
	if m.focus == paneContext {
		ctxStyle = focusStyle
	}
	context := ctxStyle.Width(rightWidth).Height(paneHeight).Render(ctxHeader + "\n" + strings.Join(ctxVisible, "\n"))

	// Tasks pane
	taskHeader := headerStyle.Render("Tasks")
	if m.loading["tasks"] {
		taskHeader += " " + loadingStyle.Render("⟳")
	}
	taskVisible := visibleSlice(m.taskLines, m.taskScroll, paneHeight-1)
	taskRendered := make([]string, len(taskVisible))
	for i, line := range taskVisible {
		globalIdx := m.taskScroll + i
		if m.focus == paneTasks && globalIdx == m.taskSelectedIdx {
			taskRendered[i] = "> " + line
		} else {
			taskRendered[i] = "  " + line
		}
	}
	if m.focus == paneTasks && len(m.taskIDs) > 0 {
		taskHeader += loadingStyle.Render(" [d]one [x]rm")
	}
	tStyle := panelStyle
	if m.focus == paneTasks {
		tStyle = focusStyle
	}
	tasks := tStyle.Width(rightWidth).Height(paneHeight).Render(taskHeader + "\n" + strings.Join(taskRendered, "\n"))

	// Skills pane
	skillHeader := headerStyle.Render("Skills")
	if m.loading["skills"] {
		skillHeader += " " + loadingStyle.Render("⟳")
	}
	skillVisible := visibleSlice(m.skillLines, m.skillScroll, paneHeight-1)
	sStyle := panelStyle
	if m.focus == paneSkills {
		sStyle = focusStyle
	}
	skills := sStyle.Width(rightWidth).Height(paneHeight).Render(skillHeader + "\n" + strings.Join(skillVisible, "\n"))

	// Status pane
	statusHeader := headerStyle.Render("Status")
	statusContent := m.statusLine
	if m.errorLine != "" {
		statusContent += "\n" + errStyle.Render("ERR: "+m.errorLine)
	}
	stStyle := panelStyle
	if m.focus == paneStatus {
		stStyle = focusStyle
	}
	status := stStyle.Width(rightWidth).Height(paneHeight).Render(statusHeader + "\n" + statusContent)

	right := lipgloss.JoinVertical(lipgloss.Top, context, tasks, skills, status)
	main := lipgloss.JoinHorizontal(lipgloss.Top, chat, right)

	// Overlays
	if m.showPicker {
		pickerLines := []string{headerStyle.Render("Session Picker")}
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
		picker := focusStyle.Width(m.width - 4).Render(strings.Join(pickerLines, "\n"))
		return lipgloss.JoinVertical(lipgloss.Top, main, picker)
	}

	if m.showIngest {
		ingest := focusStyle.Width(m.width - 4).Render(
			headerStyle.Render("Ingest Picker") + "\nEnter file path and press Enter\n" + m.ingestInput,
		)
		return lipgloss.JoinVertical(lipgloss.Top, main, ingest)
	}

	if m.showHelp {
		help := focusStyle.Width(m.width - 4).Render(strings.Join([]string{
			headerStyle.Render("Shortcuts"),
			"q: quit              esc: close overlay",
			"tab / shift+tab: switch focus pane",
			"j/k or ↑/↓: scroll / select task",
			"pgup/pgdown: fast scroll",
			"ctrl+r: refresh tasks/skills/sessions",
			"ctrl+s: session picker",
			"ctrl+o: ingest file picker",
			"ctrl+a: analyze project",
			"d: mark selected task done (tasks pane)",
			"x: remove selected task (tasks pane)",
			"?: help toggle",
		}, "\n"))
		return lipgloss.JoinVertical(lipgloss.Top, main, help)
	}

	return main
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
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

func readIDsFromJSON(content string, arrPath string) []int {
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
	ids := make([]int, 0, len(rawArr))
	for _, row := range rawArr {
		obj, ok := row.(map[string]any)
		if !ok {
			continue
		}
		if id, ok := obj["id"].(float64); ok {
			ids = append(ids, int(id))
		}
	}
	return ids
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
