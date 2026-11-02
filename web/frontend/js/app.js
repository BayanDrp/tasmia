// المسمّع الذكي: the frontend brain.
// Pick ayat → record recitation → receive word-by-word verdict.

const SURAHS = [
	"الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف",
	"الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر",
	"النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون",
	"النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم",
	"لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص",
	"الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية",
	"الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم",
	"القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة",
	"الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحريم", "الملك",
	"القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القيامة",
	"الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التكوير", "الانفطار",
	"المطففين", "الانشقاق", "البروج", "الطارق", "الأعلى", "الغاشية", "الفجر",
	"البلد", "الشمس", "الليل", "الضحى", "الشرح", "التين", "العلق", "القدر",
	"البينة", "الزلزلة", "العاديات", "القارعة", "التكاثر", "العصر", "الهمزة",
	"الفيل", "قريش", "الماعون", "الكوثر", "الكافرون", "النصر", "المسد",
	"الإخلاص", "الفلق", "الناس",
];

const STATUS_LABELS = {
	ok: { title: "صحيح", desc: "تلاوة صحيحة وتطابق تام", badgeClass: "ok" },
	mispronounced: { title: "قريب", desc: "اختلاف يسير في النطق أو الحركة أو الحروف", badgeClass: "mispronounced" },
	uncertain: { title: "غير مؤكد", desc: "تطابق محتمل مع انخفاض مستوى الثقة", badgeClass: "uncertain" },
	wrong: { title: "خطأ", desc: "اختلاف واضح في الكلمة", badgeClass: "wrong" },
	missing: { title: "ناقص", desc: "كلمة مفقودة لم تُتْلَ في هذا الموضع", badgeClass: "missing" },
	repeated: { title: "مكرر", desc: "تكرار للكلمة (تصحيح ذاتي أو ترجيع)", badgeClass: "repeated" },
	extra: { title: "زائد", desc: "كلمة زائدة لا وجود لها في هذا الموضع", badgeClass: "extra" },
};

// Offline cache for initial loading
const FALLBACK_SURAHS = {
	94: {
		surah: 94,
		surah_name: "الشرح",
		total_verses: 8,
		words: [
			{ index: 0, ayah: 1, text: "اَلَمْ" },
			{ index: 1, ayah: 1, text: "نَشْرَحْ" },
			{ index: 2, ayah: 1, text: "لَكَ" },
			{ index: 3, ayah: 1, text: "صَدْرَكَ" },
			{ index: 4, ayah: 2, text: "وَوَضَعْنَا" },
			{ index: 5, ayah: 2, text: "عَنكَ" },
			{ index: 6, ayah: 2, text: "وِزْرَكَ" },
			{ index: 7, ayah: 3, text: "اَ۬لذِےٓ" },
			{ index: 8, ayah: 3, text: "أَنقَضَ" },
			{ index: 9, ayah: 3, text: "ظَهْرَكَ" },
			{ index: 10, ayah: 4, text: "وَرَفَعْنَا" },
			{ index: 11, ayah: 4, text: "لَكَ" },
			{ index: 12, ayah: 4, text: "ذِكْرَكَ" },
			{ index: 13, ayah: 5, text: "فَإِنَّ" },
			{ index: 14, ayah: 5, text: "مَعَ" },
			{ index: 15, ayah: 5, text: "اَ۬لْعُسْرِ" },
			{ index: 16, ayah: 5, text: "يُسْراً" },
			{ index: 17, ayah: 6, text: "اِنَّ" },
			{ index: 18, ayah: 6, text: "مَعَ" },
			{ index: 19, ayah: 6, text: "اَ۬لْعُسْرِ" },
			{ index: 20, ayah: 6, text: "يُسْراٗ" },
			{ index: 21, ayah: 7, text: "فَإِذَا" },
			{ index: 22, ayah: 7, text: "فَرَغْتَ" },
			{ index: 23, ayah: 7, text: "فَانصَبْ" },
			{ index: 24, ayah: 8, text: "وَإِلَىٰ" },
			{ index: 25, ayah: 8, text: "رَبِّكَ" },
			{ index: 26, ayah: 8, text: "فَارْغَبْ" }
		]
	},
	1: {
		surah: 1,
		surah_name: "الفاتحة",
		total_verses: 7,
		words: [
			{ index: 0, ayah: 1, text: "اِ۬لْحَمْدُ" },
			{ index: 1, ayah: 1, text: "لِلهِ" },
			{ index: 2, ayah: 1, text: "رَبِّ" },
			{ index: 3, ayah: 1, text: "اِ۬لْعَٰلَمِينَ" },
			{ index: 4, ayah: 2, text: "اَ۬لرَّحْمَٰنِ" },
			{ index: 5, ayah: 2, text: "اِ۬لرَّحِيمِ" },
			{ index: 6, ayah: 3, text: "مَلِكِ" },
			{ index: 7, ayah: 3, text: "يَوْمِ" },
			{ index: 8, ayah: 3, text: "اِ۬لدِّينِ" },
			{ index: 9, ayah: 4, text: "إِيَّاكَ" },
			{ index: 10, ayah: 4, text: "نَعْبُدُ" },
			{ index: 11, ayah: 4, text: "وَإِيَّاكَ" },
			{ index: 12, ayah: 4, text: "نَسْتَعِينُ" },
			{ index: 13, ayah: 5, text: "اِ۬هْدِنَا" },
			{ index: 14, ayah: 5, text: "اِ۬لصِّرَٰطَ" },
			{ index: 15, ayah: 5, text: "اِ۬لْمُسْتَقِيمَ" },
			{ index: 16, ayah: 6, text: "صِرَٰطَ" },
			{ index: 17, ayah: 6, text: "اَ۬لَّذِينَ" },
			{ index: 18, ayah: 6, text: "أَنْعَمْتَ" },
			{ index: 19, ayah: 6, text: "عَلَيْهِمْ" },
			{ index: 20, ayah: 7, text: "غَيْرِ" },
			{ index: 21, ayah: 7, text: "اِ۬لْمَغْضُوبِ" },
			{ index: 22, ayah: 7, text: "عَلَيْهِمْ" },
			{ index: 23, ayah: 7, text: "وَلَا" },
			{ index: 24, ayah: 7, text: "اَ۬لضَّآلِّينَ" }
		]
	}
};

const $ = (id) => document.getElementById(id);

let surahWords = [];
let totalVerses = 0;
let recorder = null;
let recordingStream = null;
let chunks = [];
let isRecording = false;
let holdStartTime = 0;
let isHolding = false;
let processing = false;
let surahRequestId = 0;
let recordingTimer = null;
let recordingSeconds = 0;
let recordingCancelled = false;

const MAX_RECORDING_MS = 180_000;

const RECITE_PROFILES = {
	checked: {
		model: "quick",
		mode: "standard",
		hint: "مع التشكيل، يكشف أخطاء الحركات",
	},
	expert: {
		model: "warsh",
		mode: "standard",
		hint: "أبطأ وأكثر تفصيلاً",
	},
};

init();

function init() {
	populateSurahsDropdown();

	const urlParams = new URLSearchParams(window.location.search);
	const paramSurah = urlParams.get("surah");
	if (paramSurah && Number(paramSurah) >= 1 && Number(paramSurah) <= 114) {
		$("surah").value = String(paramSurah);
	} else {
		$("surah").value = "94"; // Surah Ash-Sharh by default
	}

	$("surah").addEventListener("change", loadSurah);
	$("from").addEventListener("change", () => onRangeChange("from"));
	$("to").addEventListener("change", () => onRangeChange("to"));
	$("model").addEventListener("change", () => {
		updateModeHint();
		clearVerdict("تغيّر وضع التسميع · جاهز للتسميع");
	});
	updateModeHint();

	// Microphone controls: Tap-to-toggle + Hold-to-record
	const mic = $("mic");
	mic.addEventListener("pointerdown", onMicPointerDown);
	window.addEventListener("pointerup", onMicPointerUp);
	window.addEventListener("pointercancel", onMicPointerCancel);

	mic.addEventListener("keydown", (event) => {
		if ((event.key === " " || event.key === "Enter") && !event.repeat) {
			event.preventDefault();
			toggleRecording();
		}
	});

	$("cancel-rec").addEventListener("click", cancelRecording);
	$("close-detail").addEventListener("click", hideWordDetail);
	$("audio-file").addEventListener("change", onAudioFileSelected);

	document.addEventListener("visibilitychange", () => {
		if (document.hidden && isRecording) {
			stopRecordingAndSubmit();
		}
	});

	// Register PWA Service Worker if available
	if ("serviceWorker" in navigator) {
		navigator.serviceWorker.register("/sw.js").catch(() => {});
	}

	loadSurah();
}

function currentProfile() {
	return RECITE_PROFILES[$("model").value] || RECITE_PROFILES.checked;
}

function updateModeHint() {
	const hint = $("mode-hint");
	if (hint) {
		hint.textContent = currentProfile().hint;
	}
}

function populateSurahsDropdown() {
	const surahSelect = $("surah");
	surahSelect.replaceChildren();
	SURAHS.forEach((name, i) => {
		const opt = document.createElement("option");
		opt.value = String(i + 1);
		opt.textContent = `${i + 1} · ${name}`;
		surahSelect.appendChild(opt);
	});
}

function toArabicNumerals(num) {
	const digits = ["٠", "١", "٢", "٣", "٤", "٥", "٦", "٧", "٨", "٩"];
	return String(num).replace(/\d/g, (d) => digits[Number(d)]);
}

/* ---- Mushaf Text Loading & Rendering ---- */

async function loadSurah() {
	const requestId = ++surahRequestId;
	const surahNumber = Number($("surah").value);

	setStatus("جاري تحميل السورة...");
	clearVerdict("");
	setPickersDisabled(true);
	$("mic").disabled = true;

	try {
		const res = await fetch(`/api/text?surah=${surahNumber}`);
		let data;
		if (res.ok) {
			data = await res.json();
		} else if (FALLBACK_SURAHS[surahNumber]) {
			data = FALLBACK_SURAHS[surahNumber];
		} else {
			const errData = await readResponse(res);
			throw new Error(errData.detail || errData.error || `HTTP ${res.status}`);
		}

		if (requestId !== surahRequestId) return;

		if (!Array.isArray(data.words) || data.words.length === 0) {
			throw new Error("لم تصل كلمات السورة من الخدمة.");
		}

		surahWords = data.words;
		totalVerses = data.total_verses || maxAyahInWords();

		refillAyahPickers(totalVerses);

		const urlParams = new URLSearchParams(window.location.search);
		const fromParam = urlParams.get("from");
		const toParam = urlParams.get("to");
		if (fromParam && Number(fromParam) >= 1 && Number(fromParam) <= totalVerses) {
			$("from").value = String(fromParam);
		} else {
			$("from").value = "1";
		}
		if (toParam && Number(toParam) >= Number($("from").value) && Number(toParam) <= totalVerses) {
			$("to").value = String(toParam);
		} else {
			$("to").value = String(totalVerses);
		}

		displayRange();
		setStatus("جاهز للتسميع");
	} catch (err) {
		if (requestId !== surahRequestId) return;

		if (FALLBACK_SURAHS[surahNumber]) {
			const data = FALLBACK_SURAHS[surahNumber];
			surahWords = data.words;
			totalVerses = data.total_verses;
			refillAyahPickers(totalVerses);
			$("from").value = "1";
			$("to").value = String(totalVerses);
			displayRange();
			setStatus("جاهز (نسخة محلية)");
		} else {
			surahWords = [];
			$("from").replaceChildren();
			$("to").replaceChildren();
			$("text").textContent = `تعذر تحميل السورة: ${err.message}`;
			setStatus("تعذر التحميل");
		}
	} finally {
		if (requestId === surahRequestId) {
			setPickersDisabled(false);
			$("mic").disabled = false;
		}
	}
}

function maxAyahInWords() {
	return surahWords.reduce((m, w) => Math.max(m, w.ayah), 1);
}

function refillAyahPickers(count) {
	const fromPicker = $("from");
	const toPicker = $("to");
	fromPicker.replaceChildren();
	toPicker.replaceChildren();

	for (let a = 1; a <= count; a++) {
		const arabicNum = toArabicNumerals(a);
		const optFrom = document.createElement("option");
		optFrom.value = String(a);
		optFrom.textContent = `${a} (${arabicNum})`;
		fromPicker.appendChild(optFrom);

		const optTo = document.createElement("option");
		optTo.value = String(a);
		optTo.textContent = `${a} (${arabicNum})`;
		toPicker.appendChild(optTo);
	}
}

function onRangeChange(changed) {
	const from = $("from");
	const to = $("to");
	const fromVal = Number(from.value);
	const toVal = Number(to.value);

	if (changed === "from" && fromVal > toVal) {
		to.value = from.value;
	}
	if (changed === "to" && toVal < fromVal) {
		from.value = to.value;
	}
	clearVerdict("جاهز للتسميع");
}

function displayRange() {
	const from = Number($("from").value) || 1;
	const to = Number($("to").value) || totalVerses || maxAyahInWords();
	const box = $("text");
	box.classList.remove("verdict");
	box.replaceChildren();

	const inRange = surahWords.filter((w) => w.ayah >= from && w.ayah <= to);
	if (!inRange.length) {
		box.textContent = "لا توجد آيات ضمن هذا النطاق.";
		return;
	}

	const fragment = document.createDocumentFragment();
	let currentAyah = inRange[0].ayah;

	inRange.forEach((w) => {
		if (w.ayah !== currentAyah) {
			fragment.appendChild(createAyahBadge(currentAyah));
			currentAyah = w.ayah;
		}
		const span = document.createElement("span");
		span.className = "word";
		span.textContent = w.text + " ";
		span.dataset.expected = w.text;
		span.dataset.ayah = String(w.ayah);
		span.dataset.index = String(w.index);
		span.tabIndex = 0;
		span.setAttribute("role", "button");
		span.setAttribute("aria-label", `كلمة: ${w.text}، آية ${w.ayah}`);

		span.addEventListener("click", () => showWordDetail({
			expected: w.text,
			heard: null,
			status: "untested",
			ayah: w.ayah,
		}, span));

		fragment.appendChild(span);
	});

	fragment.appendChild(createAyahBadge(currentAyah));
	box.appendChild(fragment);
	hideWordDetail();
}

function createAyahBadge(ayahNumber) {
	const badge = document.createElement("span");
	badge.className = "ayah-badge";
	badge.textContent = ` ﴿${toArabicNumerals(ayahNumber)}﴾ `;
	badge.setAttribute("aria-label", `نهاية الآية ${ayahNumber}`);
	return badge;
}

function clearVerdict(status = "جاهز للتسميع") {
	hideScore();
	hideWordDetail();
	displayRange();
	if (status) setStatus(status);
}

function setStatus(message) {
	$("status").textContent = message;
}

function setPickersDisabled(disabled) {
	["surah", "from", "to", "model", "audio-file"].forEach((id) => {
		const el = $(id);
		if (el) el.disabled = disabled;
	});
	$("upload-label").style.pointerEvents = disabled ? "none" : "auto";
}

async function readResponse(response) {
	const body = await response.text();
	try {
		return JSON.parse(body);
	} catch {
		return { detail: body || `HTTP ${response.status}` };
	}
}

/* ---- Microphone & Recording Controller ---- */

function onMicPointerDown(e) {
	if (e.button !== undefined && e.button !== 0) return; // Main click only
	if (processing) return;

	if (isRecording) {
		// Second tap while recording -> stop & submit
		stopRecordingAndSubmit();
		return;
	}

	holdStartTime = Date.now();
	isHolding = true;
	startRecording();
}

function onMicPointerUp() {
	if (!isHolding || !isRecording) {
		isHolding = false;
		return;
	}
	const holdDuration = Date.now() - holdStartTime;
	isHolding = false;

	// If held for more than 500ms, user was holding -> stop on release
	// If held for less than 500ms, user tapped -> keep recording until next tap
	if (holdDuration >= 500) {
		stopRecordingAndSubmit();
	}
}

function onMicPointerCancel() {
	isHolding = false;
}

function toggleRecording() {
	if (processing) return;
	if (isRecording) {
		stopRecordingAndSubmit();
	} else {
		startRecording();
	}
}

async function startRecording() {
	if (isRecording || processing) return;

	if (!surahWords.length) {
		setStatus("انتظر حتى يكتمل تحميل نص السورة.");
		return;
	}

	if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
		setStatus("التسجيل عبر الميكروفون غير مدعوم في هذا المتصفح؛ يمكنك رفع ملف صوتي.");
		return;
	}

	recordingCancelled = false;
	chunks = [];

	try {
		const stream = await navigator.mediaDevices.getUserMedia({
			audio: {
				channelCount: 1,
				sampleRate: 16000,
				echoCancellation: true,
				noiseSuppression: true,
				autoGainControl: true,
			},
		});

		if (recordingCancelled) {
			stream.getTracks().forEach((track) => track.stop());
			return;
		}

		recordingStream = stream;

		const preferredTypes = [
			"audio/webm;codecs=opus",
			"audio/mp4",
			"audio/ogg;codecs=opus",
			"audio/webm",
			"audio/wav",
		];
		const mimeType = preferredTypes.find((type) => MediaRecorder.isTypeSupported(type)) || "";

		recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);

		recorder.ondataavailable = (ev) => {
			if (ev.data && ev.data.size > 0) {
				chunks.push(ev.data);
			}
		};

		recorder.onstop = () => {
			const recordedChunks = chunks.slice();
			chunks = [];
			const mime = recorder?.mimeType || mimeType || "audio/webm";
			releaseRecordingStream();
			cleanupRecordingUI();

			if (!recordingCancelled) {
				sendRecording(recordedChunks, mime);
			}
		};

		// 250ms timeslice ensures chunks arrive continuously
		recorder.start(250);
		isRecording = true;
		setupRecordingUI();
	} catch (err) {
		const wasRecording = document.body.classList.contains("recording");
		releaseRecordingStream();
		cleanupRecordingUI();
		if (wasRecording) displayRange();
		setStatus(`تعذر تشغيل الميكروفون: ${err.message || "تحقق من منح الإذن"}`);
	}
}

function setupRecordingUI() {
	document.body.classList.add("recording");
	$("mic").setAttribute("aria-pressed", "true");
	$("mic").setAttribute("aria-label", "اضغط لإيقاف التسجيل والتحليل");
	$("cancel-rec").hidden = false;
	$("rec-timer").hidden = false;
	setPickersDisabled(true);
	showRecordingState();

	recordingSeconds = 0;
	updateTimerDisplay(0);

	recordingTimer = window.setInterval(() => {
		recordingSeconds++;
		updateTimerDisplay(recordingSeconds);
		if (recordingSeconds * 1000 >= MAX_RECORDING_MS) {
			setStatus("وصل التسجيل للحد الأقصى (3 دقائق)؛ جارٍ تحليله...");
			stopRecordingAndSubmit();
		}
	}, 1000);

	setStatus("سجّل تلاوتك الآن... اضغط مجددًا أو ارفع إصبعك عند الانتهاء.");
}

function updateTimerDisplay(seconds) {
	const mins = Math.floor(seconds / 60);
	const secs = seconds % 60;
	$("rec-timer").textContent = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

/* While the microphone is open the mushaf is hidden: the reciter should
   listen to their own voice, not read ahead. The words come back only
   after the judge answers, painted with their verdict colors. */

function showRecordingState() {
	const box = $("text");
	box.classList.remove("verdict");
	const reserved = Math.max(124, Math.min(box.offsetHeight, 360));
	box.replaceChildren();
	hideScore();
	hideWordDetail();

	const state = document.createElement("div");
	state.className = "recording-state";
	state.style.minHeight = `${reserved}px`;

	const dot = document.createElement("span");
	dot.className = "recording-dot";
	dot.setAttribute("aria-hidden", "true");

	const label = document.createElement("span");
	label.textContent = "سجّل تلاوتك الآن...";

	state.append(dot, label);
	box.appendChild(state);
}

function showProcessingState() {
	const box = $("text");
	box.classList.remove("verdict");
	const reserved = Math.max(124, Math.min(box.offsetHeight, 360));
	box.replaceChildren();
	hideScore();
	hideWordDetail();

	const state = document.createElement("div");
	state.className = "processing-state";
	state.style.minHeight = `${reserved}px`;

	const spinner = document.createElement("span");
	spinner.className = "spinner";
	spinner.setAttribute("aria-hidden", "true");

	const label = document.createElement("span");
	label.textContent = "جارٍ تحليل تلاوتك...";

	state.append(spinner, label);
	box.appendChild(state);
}

function hideScore() {
	const score = $("score");
	score.hidden = true;
	score.replaceChildren();
}

function stopRecordingAndSubmit() {
	if (!isRecording || !recorder) return;
	isHolding = false;
	if (recorder.state === "recording") {
		recorder.stop();
		showProcessingState();
		setStatus("جاري تحليل التلاوة عبر الذكاء الاصطناعي...");
	}
}

function cancelRecording() {
	recordingCancelled = true;
	isHolding = false;
	if (recorder && recorder.state === "recording") {
		recorder.stop();
	} else {
		releaseRecordingStream();
		cleanupRecordingUI();
	}
	displayRange();
	setStatus("تم إلغاء التسجيل.");
}

function cleanupRecordingUI() {
	isRecording = false;
	isHolding = false;
	document.body.classList.remove("recording");
	$("mic").setAttribute("aria-pressed", "false");
	$("mic").setAttribute("aria-label", "اضغط للتسميع");
	$("cancel-rec").hidden = true;
	$("rec-timer").hidden = true;

	if (recordingTimer) {
		window.clearInterval(recordingTimer);
		recordingTimer = null;
	}
}

function releaseRecordingStream() {
	if (recordingStream) {
		recordingStream.getTracks().forEach((track) => track.stop());
		recordingStream = null;
	}
}

async function sendRecording(recordedChunks, mimeType) {
	const blob = new Blob(recordedChunks, { type: mimeType || "audio/webm" });
	const ext = mimeType.includes("mp4") ? "m4a"
		: mimeType.includes("ogg") ? "ogg"
		: mimeType.includes("wav") ? "wav"
		: "webm";
	return submitAudio(blob, `recitation.${ext}`);
}

function onAudioFileSelected(event) {
	const file = event.target.files?.[0];
	if (!file) return;

	if (isRecording || processing) {
		setStatus("انتظر حتى يكتمل التسجيل أو التحليل الحالي.");
		event.target.value = "";
		return;
	}

	clearVerdict("جاري تجهيز الملف...");
	return submitAudio(file, file.name);
}

async function submitAudio(blob, filename) {
	if (!blob || blob.size < 100) {
		displayRange();
		setStatus("التسجيل فارغ؛ حاول مرة أخرى بصوت واضح.");
		return;
	}

	processing = true;
	setPickersDisabled(true);
	$("mic").disabled = true;
	showProcessingState();

	const form = new FormData();
	const profile = currentProfile();
	form.append("audio", blob, filename);
	form.append("model", profile.model);
	form.append("mode", profile.mode);
	form.append("surah", $("surah").value);
	form.append("ayah_from", $("from").value);
	form.append("ayah_to", $("to").value);

	try {
		const res = await fetch("/api/recite", { method: "POST", body: form });
		const data = await readResponse(res);
		if (!res.ok) {
			displayRange();
			setStatus(data.detail || data.error || "تعذر تحليل التلاوة");
			return;
		}
		paintVerdict(data);
	} catch (err) {
		displayRange();
		setStatus(`تعذر الاتصال بالخدمة: ${err.message || "تحقق من الاتصال بالخادم"}`);
	} finally {
		processing = false;
		recorder = null;
		setPickersDisabled(false);
		$("mic").disabled = false;
		$("audio-file").value = "";
	}
}

/* ---- Painting the Verdict (Zero DOM Desync) ---- */

function paintVerdict(session) {
	const box = $("text");
	box.classList.add("verdict");
	box.replaceChildren();

	const extrasByIndex = new Map();
	(session.extras || []).forEach((extra) => {
		const list = extrasByIndex.get(extra.after_index) || [];
		list.push(extra);
		extrasByIndex.set(extra.after_index, list);
	});

	const fragment = document.createDocumentFragment();

	// Extras before the first word
	for (const extra of extrasByIndex.get(-1) || []) {
		fragment.appendChild(createExtraWordSpan(extra));
	}

	let currentAyah = session.words?.[0]?.ayah || 1;

	(session.words || []).forEach((w, index) => {
		if (w.ayah !== currentAyah) {
			fragment.appendChild(createAyahBadge(currentAyah));
			currentAyah = w.ayah;
		}

		const span = document.createElement("span");
		span.className = `word ${w.status}`;
		span.textContent = w.expected + " ";
		span.style.animationDelay = `${Math.min(index * 12, 600)}ms`;
		span.tabIndex = 0;
		span.setAttribute("role", "button");
		span.setAttribute("aria-label", `كلمة: ${w.expected}، الحالة: ${STATUS_LABELS[w.status]?.title || w.status}`);

		span.addEventListener("click", () => showWordDetail(w, span));
		span.addEventListener("keydown", (e) => {
			if (e.key === "Enter" || e.key === " ") {
				e.preventDefault();
				showWordDetail(w, span);
			}
		});

		fragment.appendChild(span);

		// Extras after this word
		for (const extra of extrasByIndex.get(index) || []) {
			fragment.appendChild(createExtraWordSpan(extra));
		}
	});

	if (session.words?.length) {
		fragment.appendChild(createAyahBadge(currentAyah));
	}

	box.appendChild(fragment);
	renderScoreCard(session);

	const latencyText = session.latency_ms ? ` خلال ${(session.latency_ms / 1000).toFixed(1)} ثانية` : "";
	setStatus(`تم التحليل بنجاح${latencyText}. اضغط على أي كلمة لعرض تفاصيلها.`);
}

function createExtraWordSpan(extra) {
	const span = document.createElement("span");
	span.className = "word extra";
	span.textContent = extra.text + " ";
	span.tabIndex = 0;
	span.setAttribute("role", "button");
	span.setAttribute("aria-label", `كلمة زائدة: ${extra.text}`);

	span.addEventListener("click", () => showWordDetail({
		expected: "-",
		heard: extra.text,
		status: "extra",
		ayah: null,
	}, span));

	return span;
}

function showWordDetail(wordData, element) {
	document.querySelectorAll(".word.active").forEach((el) => el.classList.remove("active"));
	if (element) element.classList.add("active");

	const detail = $("word-detail");
	const badge = $("detail-badge");
	const text = $("detail-text");
	const meta = STATUS_LABELS[wordData.status] || { title: wordData.status, desc: "", badgeClass: "uncertain" };

	badge.className = `detail-badge ${meta.badgeClass}`;
	badge.textContent = meta.title;

	let description = "";
	if (wordData.status === "extra") {
		description = `كلمة زائدة سُمعت: <strong>${wordData.heard}</strong> (لا توجد في المصحف هنا)`;
	} else if (wordData.status === "missing") {
		description = `الكلمة الأصلية: <strong>${wordData.expected}</strong> (لم تُسمع في التسجيل)`;
	} else if (wordData.status === "ok") {
		description = `الكلمة: <strong>${wordData.expected}</strong> · سُمعت: <strong>${wordData.heard || wordData.expected}</strong>`;
	} else {
		description = `الكلمة: <strong>${wordData.expected}</strong> · سُمعت: <strong>${wordData.heard || "-"}</strong> (${meta.desc})`;
	}

	text.innerHTML = description;
	detail.hidden = false;
}

function hideWordDetail() {
	$("word-detail").hidden = true;
	document.querySelectorAll(".word.active").forEach((el) => el.classList.remove("active"));
}

/* ---- Rich Score Card Rendering ---- */

function renderScoreCard(session) {
	const scoreContainer = $("score");
	scoreContainer.replaceChildren();

	const c = session.counts || {};
	const pct = (x) => Math.round((x || 0) * 100);
	const scorePct = pct(session.score);
	const accPct = pct(session.strict_accuracy);

	const card = document.createElement("div");
	card.className = "score-card";

	card.innerHTML = `
		<div class="score-head">
			<div class="score-main">
				<span class="score-title">النتيجة الإجمالية</span>
				<span class="score-number">${scorePct}٪</span>
			</div>
			<div class="score-meta">
				<div>تطابق تام: <strong>${accPct}٪</strong></div>
				<div>الكلمات: <strong>${session.total_words || 0}</strong></div>
			</div>
		</div>
		<div class="score-bar-track">
			<div class="score-bar-fill" style="width: ${scorePct}%;"></div>
		</div>
		<div class="score-chips">
			<span class="chip ok" data-status="ok"><span class="dot"></span> صحيح ${c.ok || 0}</span>
			<span class="chip mispronounced" data-status="mispronounced"><span class="dot"></span> قريب ${c.mispronounced || 0}</span>
			<span class="chip uncertain" data-status="uncertain"><span class="dot"></span> غير مؤكد ${c.uncertain || 0}</span>
			<span class="chip wrong" data-status="wrong"><span class="dot"></span> خطأ ${c.wrong || 0}</span>
			<span class="chip missing" data-status="missing"><span class="dot"></span> ناقص ${c.missing || 0}</span>
			<span class="chip repeated" data-status="repeated"><span class="dot"></span> مكرر ${c.repeated || 0}</span>
			<span class="chip extra" data-status="extra"><span class="dot"></span> زائد ${c.extra || 0}</span>
		</div>
	`;

	// Filter / highlight words when clicking status chips
	card.querySelectorAll(".chip").forEach((chip) => {
		chip.addEventListener("click", () => {
			const status = chip.dataset.status;
			const matchingWords = document.querySelectorAll(`.word.${status}`);
			if (matchingWords.length > 0) {
				matchingWords.forEach((w) => {
					w.style.transition = "transform 0.2s ease";
					w.style.transform = "scale(1.2)";
					setTimeout(() => { w.style.transform = "none"; }, 350);
				});
				matchingWords[0].scrollIntoView({ behavior: "smooth", block: "center" });
			}
		});
	});

	scoreContainer.appendChild(card);
	scoreContainer.hidden = false;
}
