(() => {
  const tree = document.querySelector('[data-org-tree]');
  if (!tree) return;

  const escapeHtml = (value) => String(value || '').replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;'
  }[character]));

  const createTree = (rows) => {
    const nodes = rows.map((row, index) => ({
      ...row,
      key: `${row.id}-${index}`,
      children: []
    }));
    const byParent = new Map();

    nodes.forEach((node) => {
      const children = byParent.get(node.parentId) || [];
      children.push(node);
      byParent.set(node.parentId, children);
    });

    nodes.forEach((node) => {
      node.children = byParent.get(node.id) || [];
    });

    return nodes.find((node) => !node.parentId);
  };

  const render = (root) => {
    const renderBranch = (node) => {
      const branch = document.createElement('div');
      branch.className = 'org-tree__branch';
      branch.dataset.nodeKey = node.key;

      const card = document.createElement('article');
      card.className = 'org-tree__card';
      if (node.children.length) card.classList.add('org-tree__card--parent');
      card.innerHTML = `
        <img class="org-tree__photo" src="/img/photos/${escapeHtml(node.image)}" alt="" />
        <span class="org-tree__name">${escapeHtml(node.name)} ${escapeHtml(node.lastName)}</span>
        <span class="org-tree__position">${escapeHtml(node.position)}</span>
      `;

      if (node.children.length) {
        const toggle = document.createElement('button');
        toggle.className = 'org-tree__toggle';
        toggle.type = 'button';
        toggle.setAttribute('aria-expanded', 'true');
        toggle.setAttribute('aria-label', `Collapse ${node.name} ${node.lastName}`);
        toggle.textContent = '-';
        const collapseBranch = (targetBranch) => {
          const targetToggle = targetBranch.querySelector(':scope > .org-tree__card .org-tree__toggle');
          const targetChildren = targetBranch.querySelector(':scope > .org-tree__children');
          if (!targetToggle || !targetChildren) return;
          targetChildren.hidden = true;
          targetToggle.setAttribute('aria-expanded', 'false');
          targetToggle.setAttribute('aria-label', `Expand ${targetToggle.dataset.nodeName}`);
          targetToggle.textContent = '+';
        };

        const toggleBranch = () => {
          const children = branch.querySelector(':scope > .org-tree__children');
          const expanded = toggle.getAttribute('aria-expanded') === 'true';

          if (!expanded) {
            branch.parentElement.querySelectorAll(':scope > .org-tree__branch').forEach((sibling) => {
              if (sibling !== branch) collapseBranch(sibling);
            });
          }

          children.hidden = expanded;
          toggle.setAttribute('aria-expanded', String(!expanded));
          toggle.setAttribute('aria-label', `${expanded ? 'Expand' : 'Collapse'} ${node.name} ${node.lastName}`);
          toggle.textContent = expanded ? '+' : '-';
        };

        toggle.dataset.nodeName = `${node.name} ${node.lastName}`;
        toggle.addEventListener('click', (event) => {
          event.stopPropagation();
          toggleBranch();
        });
        card.addEventListener('click', toggleBranch);
        card.append(toggle);
      }

      branch.append(card);

      if (node.children.length) {
        const children = document.createElement('div');
        children.className = 'org-tree__children';
        if (node.children.length === 1) children.classList.add('org-tree__children--single');
        node.children.forEach((child) => children.append(renderBranch(child)));
        branch.append(children);
      }

      return branch;
    };

    tree.replaceChildren(renderBranch(root));
  };

  const setAllExpanded = (expanded) => {
    tree.querySelectorAll('.org-tree__toggle').forEach((toggle) => {
      const branch = toggle.closest('.org-tree__branch');
      const children = branch.querySelector(':scope > .org-tree__children');
      children.hidden = !expanded;
      toggle.setAttribute('aria-expanded', String(expanded));
      toggle.textContent = expanded ? '-' : '+';
    });
  };

  const setInitialExpanded = (root) => {
    tree.querySelectorAll('.org-tree__toggle').forEach((toggle) => {
      const branch = toggle.closest('.org-tree__branch');
      if (branch.dataset.nodeKey === root.key) return;

      const children = branch.querySelector(':scope > .org-tree__children');
      children.hidden = true;
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-label', toggle.getAttribute('aria-label').replace('Collapse', 'Expand'));
      toggle.textContent = '+';
    });
  };

  fetch('/data/org-chart.csv')
    .then((response) => response.text())
    .then((csv) => {
      const rows = d3.csvParse(csv);
      const root = createTree(rows);
      if (!root) throw new Error('Organization chart has no root node.');
      render(root);
      setInitialExpanded(root);

      document.querySelectorAll('[data-org-action]').forEach((button) => {
        button.addEventListener('click', () => {
          setAllExpanded(button.dataset.orgAction === 'expand');
        });
      });
    })
    .catch(() => {
      tree.innerHTML = '<p class="org-chart__placeholder">The organization chart could not be loaded.</p>';
    });
})();
