ALTER TABLE `lpu` ADD COLUMN `epgu2_id` INT NULL  AFTER `keyEPGU` , ADD COLUMN `epgu2_oid` VARCHAR(45) NULL  AFTER `epgu2_id` ;
ALTER TABLE `lpu` ADD COLUMN `epgu2_token` VARCHAR(45) NULL  AFTER `epgu2_oid` ;

ALTER TABLE `speciality` ADD COLUMN `epgu2_speciality_id` INT NULL  AFTER `epgu_service_type_id` , ADD COLUMN `epgu2_service_id` INT NULL  AFTER `epgu2_speciality_id` ,
  ADD CONSTRAINT `fk_speciality_2`
  FOREIGN KEY (`epgu2_speciality_id` )
  REFERENCES `soap_dev`.`epgu2_speciality` (`id` )
  ON DELETE NO ACTION
  ON UPDATE NO ACTION,
  ADD CONSTRAINT `fk_speciality_3`
  FOREIGN KEY (`epgu2_service_id` )
  REFERENCES `soap_dev`.`epgu2_service` (`id` )
  ON DELETE NO ACTION
  ON UPDATE NO ACTION
, ADD INDEX `fk_speciality_2_idx` (`epgu2_speciality_id` ASC)
, ADD INDEX `fk_speciality_3_idx` (`epgu2_service_id` ASC) ;

ALTER TABLE `personal_keyepgu` ADD COLUMN `epgu2_id` INT NULL  AFTER `keyEPGU` ;
ALTER TABLE `personal_keyepgu` ADD COLUMN `epgu2_resource_id` VARCHAR(45) NULL  AFTER `epgu2_id` ;
ALTER TABLE `personal` ADD COLUMN `snils` VARCHAR(11) NULL  AFTER `office` ;

