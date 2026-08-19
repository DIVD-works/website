const jobsGrid = document.querySelector('#jobs-grid');
const jobsEmpty = document.querySelector('#jobs-empty');
const jobsCount = document.querySelector('#jobs-count');
const searchInput = document.querySelector('#job-search');
const domainFilter = document.querySelector('#job-domain');
const typeFilter = document.querySelector('#job-type');
const languageFilter = document.querySelector('#job-language');
const skillToggle = document.querySelector('#job-skill-toggle');
const skillMenu = document.querySelector('#job-skill-menu');
const skillSearch = document.querySelector('#job-skill-search');
const skillOptions = document.querySelector('#job-skill-options');

if (jobsGrid && jobsEmpty && jobsCount) {
  let jobs = [];
  const selectedSkills = new Set();

  const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
  }[character]));

  const cardTemplate = (job) => `
    <article class="job-card">
      <div class="job-card__top">
        <h3>${escapeHtml(job.title)}</h3>
        <span class="job-card__type">${escapeHtml(job.type)}</span>
      </div>
      <p class="job-card__partner">${escapeHtml(job.partner)}</p>
      <dl class="job-card__details">
        <div><dt>Domain</dt><dd>${escapeHtml(job.domain)}</dd></div>
        <div><dt>Location</dt><dd>${escapeHtml(job.location)}</dd></div>
        <div><dt>Language</dt><dd>${escapeHtml(job.language)}</dd></div>
        <div><dt>Stipend</dt><dd>${job.stipend ? 'Available' : 'Not specified'}</dd></div>
      </dl>
      <div class="job-card__skills" aria-label="Skills">
        ${job.skills.map((skill) => `<button class="job-card__skill" type="button" data-skill="${escapeHtml(skill)}" aria-pressed="${selectedSkills.has(skill)}">${escapeHtml(skill)}</button>`).join('')}
      </div>
      <a class="button button--small" href="${escapeHtml(job.apply_url)}" target="_blank" rel="noopener noreferrer">Apply Now <span aria-hidden="true">&#8594;</span></a>
    </article>`;

  const getSkills = () => [...new Set(jobs.flatMap((job) => job.skills))].sort((firstSkill, secondSkill) => firstSkill.localeCompare(secondSkill));

  const updateSkillToggle = () => {
    skillToggle.textContent = selectedSkills.size ? `${selectedSkills.size} skills selected` : 'All skills';
    skillToggle.setAttribute('aria-expanded', String(!skillMenu.hidden));
  };

  const populateSkillFilter = () => {
    skillOptions.innerHTML = getSkills().map((skill) => `
      <label class="skills-filter__option">
        <input type="checkbox" value="${escapeHtml(skill)}" ${selectedSkills.has(skill) ? 'checked' : ''} />
        <span>${escapeHtml(skill)}</span>
      </label>`).join('');
  };

  const matches = (job) => {
    const query = searchInput.value.trim().toLowerCase();
    const searchable = [job.title, job.partner, job.location, ...job.skills].join(' ').toLowerCase();
    return (!query || searchable.includes(query))
      && (!domainFilter.value || job.domain === domainFilter.value)
      && (!typeFilter.value || job.type === typeFilter.value)
      && (!languageFilter.value || job.language.includes(languageFilter.value))
      && (!selectedSkills.size || job.skills.some((skill) => selectedSkills.has(skill)));
  };

  const render = () => {
    const visibleJobs = jobs.filter(matches);
    jobsGrid.innerHTML = visibleJobs.map(cardTemplate).join('');
    jobsEmpty.hidden = visibleJobs.length > 0;
    jobsCount.textContent = `${visibleJobs.length} ${visibleJobs.length === 1 ? 'vacancy' : 'vacancies'}`;
  };

  jobsGrid.addEventListener('click', (event) => {
    const skillButton = event.target.closest('[data-skill]');
    if (!skillButton) return;
    const skill = skillButton.dataset.skill;
    if (selectedSkills.has(skill)) selectedSkills.delete(skill);
    else selectedSkills.add(skill);
    populateSkillFilter();
    updateSkillToggle();
    render();
  });

  skillToggle.addEventListener('click', () => {
    skillMenu.hidden = !skillMenu.hidden;
    updateSkillToggle();
    if (!skillMenu.hidden) skillSearch.focus();
  });

  skillSearch.addEventListener('input', () => {
    const query = skillSearch.value.trim().toLowerCase();
    skillOptions.querySelectorAll('.skills-filter__option').forEach((option) => {
      option.hidden = !option.textContent.toLowerCase().includes(query);
    });
  });

  skillOptions.addEventListener('change', (event) => {
    const checkbox = event.target.closest('input[type="checkbox"]');
    if (!checkbox) return;
    if (checkbox.checked) selectedSkills.add(checkbox.value);
    else selectedSkills.delete(checkbox.value);
    updateSkillToggle();
    render();
  });

  fetch('/data/jobs.json')
    .then((response) => {
      if (!response.ok) throw new Error('Could not load vacancies');
      return response.json();
    })
    .then((data) => {
      jobs = data;
      populateSkillFilter();
      updateSkillToggle();
      render();
    })
    .catch(() => {
      jobsEmpty.hidden = false;
      jobsEmpty.querySelector('h3').textContent = 'Vacancies are temporarily unavailable';
      jobsEmpty.querySelector('p').textContent = 'Please check back soon for new opportunities.';
    });

  [searchInput, domainFilter, typeFilter, languageFilter, skillFilter].forEach((control) => control.addEventListener('input', render));
}
