ALTER TABLE `lpu` ADD COLUMN `epgu2_id` INT NULL  AFTER `keyEPGU` , ADD COLUMN `epgu2_oid` VARCHAR(45) NULL  AFTER `epgu2_id` ;
ALTER TABLE `lpu` ADD COLUMN `epgu2_token` VARCHAR(45) NULL  AFTER `epgu2_oid` ;


CREATE TABLE `epgu2_speciality` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(128) NOT NULL,
  `code` int(11) NOT NULL,
  `recid` int(11) NOT NULL,
  `parent_recid` varchar(32) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `recid` (`recid`)
) ENGINE=InnoDB AUTO_INCREMENT=572 DEFAULT CHARSET=utf8;

CREATE TABLE `epgu2_service` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(128) NOT NULL,
  `code` varchar(32) NOT NULL,
  `spec_recid` int(11) DEFAULT NULL,
  `speciality_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `speciality_id` (`speciality_id`),
  CONSTRAINT `epgu2_service_ibfk_1` FOREIGN KEY (`speciality_id`) REFERENCES `epgu2_speciality` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1133 DEFAULT CHARSET=utf8;


-- noinspection SqlNoDataSourceInspection
ALTER TABLE `speciality` ADD COLUMN `epgu2_speciality_id` INT NULL  AFTER `epgu_service_type_id` , ADD COLUMN `epgu2_service_id` INT NULL  AFTER `epgu2_speciality_id` ,
  ADD CONSTRAINT `fk_speciality_2`
  FOREIGN KEY (`epgu2_speciality_id` )
  REFERENCES `epgu2_speciality` (`id` )
  ON DELETE NO ACTION
  ON UPDATE NO ACTION,
  ADD CONSTRAINT `fk_speciality_3`
  FOREIGN KEY (`epgu2_service_id` )
  REFERENCES `epgu2_service` (`id` )
  ON DELETE NO ACTION
  ON UPDATE NO ACTION
, ADD INDEX `fk_speciality_2_idx` (`epgu2_speciality_id` ASC)
, ADD INDEX `fk_speciality_3_idx` (`epgu2_service_id` ASC) ;

ALTER TABLE `personal_keyepgu` ADD COLUMN `epgu2_id` INT NULL  AFTER `keyEPGU` ;
ALTER TABLE `personal_keyepgu` ADD COLUMN `epgu2_resource_id` VARCHAR(45) NULL  AFTER `epgu2_id` ;
ALTER TABLE `personal` ADD COLUMN `snils` VARCHAR(11) NULL  AFTER `office` ;

CREATE TABLE `epgu2_post` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(128) NOT NULL,
  `recid` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `recid` (`recid`)
) ENGINE=InnoDB AUTO_INCREMENT=541 DEFAULT CHARSET=utf8;

CREATE TABLE `post` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(64) NOT NULL,
  `epgu2_post_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `ix_post_epgu2_post_id` (`epgu2_post_id`),
  CONSTRAINT `post_ibfk_1` FOREIGN KEY (`epgu2_post_id`) REFERENCES `epgu2_post` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=90 DEFAULT CHARSET=utf8;

CREATE TABLE `personal_post` (
  `personal_id` bigint(20) NOT NULL,
  `post_id` int(11) NOT NULL,
  PRIMARY KEY (`personal_id`,`post_id`),
  KEY `post_id` (`post_id`),
  CONSTRAINT `personal_post_ibfk_1` FOREIGN KEY (`personal_id`) REFERENCES `personal` (`id`) ON DELETE CASCADE,
  CONSTRAINT `personal_post_ibfk_2` FOREIGN KEY (`post_id`) REFERENCES `post` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;