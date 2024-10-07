SUBDIRS = scraper tv-updater

.PHONY: docker
docker: $(SUBDIRS)_docker

.PHONY: $(SUBDIRS)_docker
$(SUBDIRS)_docker:
	$(MAKE) -C $(@:_docker=) docker
